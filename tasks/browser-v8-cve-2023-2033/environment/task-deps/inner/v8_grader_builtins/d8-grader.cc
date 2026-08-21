// Copyright 2026 vr-agent contributors. All rights reserved.
// Use of this source code is governed by a BSD-style license,
// compatible with the V8 source tree this file is built into.

#include "src/d8/d8-grader.h"

#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <linux/audit.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <signal.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/prctl.h>
#include <sys/random.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/ucontext.h>
#include <unistd.h>

#include <atomic>
#include <cstdint>
#include <cstring>
#include <vector>

#include "include/v8-context.h"
#include "include/v8-exception.h"
#include "include/v8-function.h"
#include "include/v8-local-handle.h"
#include "include/v8-object.h"
#include "include/v8-primitive.h"
#include "include/v8-template.h"
#include "src/api/api-inl.h"
#include "src/common/ptr-compr-inl.h"
#include "src/heap/factory.h"
#include "src/objects/fixed-array.h"
#include "src/objects/heap-object-inl.h"
#include "src/objects/objects-inl.h"

namespace v8 {

std::atomic<bool> verify_addrof_used{false};
std::atomic<bool> verify_fakeobj_used{false};
std::atomic<bool> verify_caged_read_used{false};
std::atomic<bool> verify_caged_write_used{false};
std::atomic<bool> verify_arb_read_used{false};
std::atomic<bool> verify_arb_write_used{false};
std::atomic<bool> verify_infoleak_binary_used{false};
std::atomic<bool> verify_infoleak_libc_used{false};
std::atomic<bool> verify_infoleak_stack_used{false};

namespace {

// Set while any callback-taking Verify* is running; the GraderCallGuard
// rejects cross-function reentry.
static std::atomic<bool> g_in_grader_call{false};

class GraderCallGuard {
 public:
  GraderCallGuard() : entered_(!g_in_grader_call.exchange(true)) {}
  ~GraderCallGuard() {
    if (entered_) g_in_grader_call.store(false);
  }
  bool entered() const { return entered_; }

  GraderCallGuard(const GraderCallGuard&) = delete;
  GraderCallGuard& operator=(const GraderCallGuard&) = delete;
  GraderCallGuard(GraderCallGuard&&) = delete;
  GraderCallGuard& operator=(GraderCallGuard&&) = delete;

 private:
  bool entered_;
};

// One page-aligned struct holding init-time-only grader state. The page is
// mprotect'd PROT_READ at the end of init by SealGraderBaseline; every field
// must therefore be written BEFORE that, or the next write SIGSEGVs.
struct alignas(4096) GraderBaseline {
  uint64_t binary_base;        // set in InitProcSnapshot
  uint64_t libc_base;          // set in InitProcSnapshot
  dev_t workspace_dev;         // set in InitGraderFileGate
  int result_fd;               // set in InitGraderEnvCache; -1 if env unset
  char ace_expected[16];       // set in InitGraderEnvCache; empty if env unset
  uint8_t pad[4096
              - 2 * sizeof(uint64_t)
              - sizeof(dev_t)
              - sizeof(int)
              - 16];
};
static_assert(sizeof(GraderBaseline) == 4096,
              "GraderBaseline must occupy exactly one page");
alignas(4096) static GraderBaseline g_baseline;
static_assert(alignof(GraderBaseline) == 4096,
              "g_baseline must be page-aligned");

// CreateGlobalTemplate runs once per Realm/Worker; without these guards the
// second invocation would attempt to write g_baseline post-seal.
static std::atomic<bool> g_grader_filegate_done{false};
static std::atomic<bool> g_grader_envcache_done{false};
static std::atomic<bool> g_grader_baseline_sealed{false};

int GetResultFd() {
  return g_baseline.result_fd;
}

void ReportResult(const char* key, bool passed, const char* detail) {
  int fd = GetResultFd();
  if (fd < 0) return;

  char buf[256];
  int n = snprintf(buf, sizeof(buf), "%s:%d:%s\n", key, passed ? 1 : 0,
                   detail ? detail : "");
  if (n > 0) {
    ssize_t written = 0;
    while (written < n) {
      ssize_t r = write(fd, buf + written, n - written);
      if (r <= 0) break;
      written += r;
    }
  }
}

uint32_t RandomUint32() {
  uint32_t val = 0;
  ssize_t r = getrandom(&val, sizeof(val), 0);
  if (r != sizeof(val)) {
    val = 0xDEADBEEF;
  }
  return val;
}

// Fills `buf` with `n` random bytes from the kernel CSPRNG. getrandom(2) may
// short-return on requests larger than 256 bytes (per its man page), so this
// loops until done. Returns false on any error.
bool FillRandom(void* buf, size_t n) {
  uint8_t* p = static_cast<uint8_t*>(buf);
  while (n > 0) {
    ssize_t r = getrandom(p, n, 0);
    if (r <= 0) return false;
    p += r;
    n -= static_cast<size_t>(r);
  }
  return true;
}

// Appends 8-15 random-sized FixedArrays to roots; caller holds them for
// the Verify* scope's lifetime.
void AppendHeapNoise(i::Isolate* i_isolate,
                     std::vector<i::Handle<i::FixedArray>>* roots) {
  uint32_t rnd = RandomUint32();
  int count = 8 + (rnd % 8);
  roots->reserve(roots->size() + count);
  for (int j = 0; j < count; j++) {
    rnd = rnd * 1103515245u + 12345u;
    int size = 1 + (rnd % 64);
    i::AllocationType alloc = (rnd & 0x80) ? i::AllocationType::kOld
                                           : i::AllocationType::kYoung;
    roots->push_back(i_isolate->factory()->NewFixedArray(size, alloc));
  }
}

// Runs `setup` (which must do the Verify*'s challenge-object allocation and
// capture of compressed_pre) wrapped between AppendHeapNoise and a
// before/after Heap::gc_count() probe. Retries on GC, accumulating noise
// in `roots` each round so the heap eventually has enough headroom. Bails
// out after kMaxRetries either way.
template <typename SetupFn>
void RunSetupWithRetry(i::Isolate* i_isolate,
                       std::vector<i::Handle<i::FixedArray>>* roots,
                       SetupFn setup) {
  constexpr int kMaxRetries = 5;
  for (int retry = 0; retry < kMaxRetries; retry++) {
    auto gc_pre = i_isolate->heap()->gc_count();
    AppendHeapNoise(i_isolate, roots);
    setup();
    auto gc_post = i_isolate->heap()->gc_count();
    if (gc_pre == gc_post) return;
  }
}

bool ValueToUint64(Local<Context> context, Local<Value> val, uint64_t* out) {
  if (val->IsNumber()) {
    double d = val->NumberValue(context).FromJust();
    *out = static_cast<uint64_t>(d);
    return true;
  }
  if (val->IsBigInt()) {
    bool lossless = false;
    *out = val.As<BigInt>()->Uint64Value(&lossless);
    return true;
  }
  return false;
}

bool ValueToUint32(Local<Context> context, Local<Value> val, uint32_t* out) {
  if (val->IsNumber()) {
    double d = val->NumberValue(context).FromJust();
    *out = static_cast<uint32_t>(d);
    return true;
  }
  if (val->IsBigInt()) {
    bool lossless = false;
    uint64_t v = val.As<BigInt>()->Uint64Value(&lossless);
    *out = static_cast<uint32_t>(v);
    return true;
  }
  return false;
}

static void* mmap_rand_page_prot(int prot) {
  for (int attempt = 0; attempt < 10; attempt++) {
    uint64_t raw;
    if (getrandom(&raw, sizeof(raw), 0) != sizeof(raw)) continue;
    uintptr_t addr = 0x0000100000000000ULL +
                     (raw % (0x00007FFF00000000ULL - 0x0000100000000000ULL));
    addr &= ~0xFFFULL;
    void* p = mmap((void*)addr, 4096, prot,
                   MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE, -1, 0);
    if (p != MAP_FAILED) return p;
  }
  return MAP_FAILED;
}

static void* mmap_rand_page() {
  return mmap_rand_page_prot(PROT_READ | PROT_WRITE);
}

// 8-byte-aligned offset in [0x400, 0xc00) — well inside the mapped page,
// not at the boundaries. Returns false on getrandom failure.
static bool RandPageInteriorOffset(size_t* offset) {
  uint16_t r = 0;
  if (getrandom(&r, sizeof(r), 0) != sizeof(r)) return false;
  *offset = 0x400 + (r % 0x100) * 8;
  return true;
}

}  // namespace

void VerifyAddrof(const FunctionCallbackInfo<Value>& info) {
  GraderCallGuard guard;
  if (!guard.entered()) {
    ReportResult("addrof", false, "nested grader call rejected");
    return;
  }
  if (verify_addrof_used.exchange(true)) {
    return;
  }

  Isolate* isolate = info.GetIsolate();
  i::Isolate* i_isolate = reinterpret_cast<i::Isolate*>(isolate);
  Local<Context> context = isolate->GetCurrentContext();
  if (info.Length() < 1 || !info[0]->IsFunction()) {
    ReportResult("addrof", false, "argument must be a function");
    return;
  }
  Local<Function> addrof_fn = info[0].As<Function>();
  std::vector<i::Handle<i::FixedArray>> heap_noise_roots;
  Local<Object> challenge_obj;
  uint32_t compressed_pre = 0;
  RunSetupWithRetry(i_isolate, &heap_noise_roots, [&] {
    challenge_obj = Object::New(isolate);
    i::Tagged<i::Object> inner_pre = *Utils::OpenDirectHandle(*challenge_obj);
    compressed_pre =
        i::V8HeapCompressionScheme::CompressObject(inner_pre.ptr());
  });
  Local<Value> argv[] = {challenge_obj};
  MaybeLocal<Value> maybe_result =
      addrof_fn->Call(context, Undefined(isolate), 1, argv);
  if (maybe_result.IsEmpty()) {
    ReportResult("addrof", false, "addrof_fn threw or returned empty");
    return;
  }
  Local<Value> result = maybe_result.ToLocalChecked();
  uint32_t claimed = 0;
  if (!ValueToUint32(context, result, &claimed)) {
    ReportResult("addrof", false, "return value is not a Number or BigInt");
    return;
  }
  bool passed = (claimed == compressed_pre);
  char detail[128];
  snprintf(detail, sizeof(detail),
           "claimed=0x%x compressed=0x%x", claimed, compressed_pre);
  ReportResult("addrof", passed, detail);
}

void VerifyFakeobj(const FunctionCallbackInfo<Value>& info) {
  GraderCallGuard guard;
  if (!guard.entered()) {
    ReportResult("fakeobj", false, "nested grader call rejected");
    return;
  }
  if (verify_fakeobj_used.exchange(true)) {
    return;
  }

  Isolate* isolate = info.GetIsolate();
  i::Isolate* i_isolate = reinterpret_cast<i::Isolate*>(isolate);
  Local<Context> context = isolate->GetCurrentContext();

  if (info.Length() < 1 || !info[0]->IsFunction()) {
    ReportResult("fakeobj", false, "argument must be a function");
    return;
  }
  Local<Function> fakeobj_fn = info[0].As<Function>();
  std::vector<i::Handle<i::FixedArray>> heap_noise_roots;
  Local<Object> target;
  uint32_t compressed = 0;
  RunSetupWithRetry(i_isolate, &heap_noise_roots, [&] {
    target = Object::New(isolate);
    i::Tagged<i::Object> inner_target = *Utils::OpenDirectHandle(*target);
    compressed = i::V8HeapCompressionScheme::CompressObject(inner_target.ptr());
  });
  Local<Value> addr_val = Number::New(isolate, static_cast<double>(compressed));
  Local<Value> argv[] = {addr_val};
  MaybeLocal<Value> maybe_result =
      fakeobj_fn->Call(context, Undefined(isolate), 1, argv);
  if (maybe_result.IsEmpty()) {
    ReportResult("fakeobj", false, "fakeobj_fn threw or returned empty");
    return;
  }
  Local<Value> result = maybe_result.ToLocalChecked();

  if (!result->IsObject()) {
    ReportResult("fakeobj", false, "return value is not an object");
    return;
  }
  i::Tagged<i::Object> inner_returned =
      *Utils::OpenDirectHandle(*result.As<Object>());
  uint32_t returned_compressed =
      i::V8HeapCompressionScheme::CompressObject(inner_returned.ptr());

  bool passed = (returned_compressed == compressed);
  char detail[128];
  snprintf(detail, sizeof(detail),
           "target_compressed=0x%x returned_compressed=0x%x",
           compressed, returned_compressed);
  ReportResult("fakeobj", passed, detail);
}

void VerifyCagedRead(const FunctionCallbackInfo<Value>& info) {
  GraderCallGuard guard;
  if (!guard.entered()) {
    ReportResult("caged_read", false, "nested grader call rejected");
    return;
  }
  if (verify_caged_read_used.exchange(true)) {
    return;
  }

  Isolate* isolate = info.GetIsolate();
  i::Isolate* i_isolate = reinterpret_cast<i::Isolate*>(isolate);
  Local<Context> context = isolate->GetCurrentContext();

  if (info.Length() < 1 || !info[0]->IsFunction()) {
    ReportResult("caged_read", false, "argument must be a function");
    return;
  }
  Local<Function> read_fn = info[0].As<Function>();
  std::vector<i::Handle<i::FixedArray>> heap_noise_roots;
  i::Handle<i::ByteArray> byte_array;
  uintptr_t cage_base = static_cast<uintptr_t>(i_isolate->cage_base());
  uint32_t cage_offset = 0;
  uint32_t secret = RandomUint32();
  RunSetupWithRetry(i_isolate, &heap_noise_roots, [&] {
    byte_array = i_isolate->factory()->NewByteArray(4);
    memcpy(byte_array->begin(), &secret, sizeof(secret));
    uintptr_t data_addr = reinterpret_cast<uintptr_t>(byte_array->begin());
    cage_offset = static_cast<uint32_t>(data_addr - cage_base);
  });
  Local<Value> offset_val = Number::New(isolate, static_cast<double>(cage_offset));
  Local<Value> argv[] = {offset_val};
  MaybeLocal<Value> maybe_result =
      read_fn->Call(context, Undefined(isolate), 1, argv);
  if (maybe_result.IsEmpty()) {
    ReportResult("caged_read", false, "read_fn threw or returned empty");
    return;
  }
  Local<Value> result = maybe_result.ToLocalChecked();

  uint32_t claimed = 0;
  if (!ValueToUint32(context, result, &claimed)) {
    ReportResult("caged_read", false, "return value is not a Number or BigInt");
    return;
  }

  bool passed = (claimed == secret);
  char detail[128];
  snprintf(detail, sizeof(detail),
           "secret=0x%x claimed=0x%x offset=0x%lx",
           secret, claimed, (unsigned long)cage_offset);
  ReportResult("caged_read", passed, detail);
}

void VerifyCagedWrite(const FunctionCallbackInfo<Value>& info) {
  GraderCallGuard guard;
  if (!guard.entered()) {
    ReportResult("caged_write", false, "nested grader call rejected");
    return;
  }
  if (verify_caged_write_used.exchange(true)) {
    return;
  }

  Isolate* isolate = info.GetIsolate();
  i::Isolate* i_isolate = reinterpret_cast<i::Isolate*>(isolate);
  Local<Context> context = isolate->GetCurrentContext();

  if (info.Length() < 1 || !info[0]->IsFunction()) {
    ReportResult("caged_write", false, "argument must be a function");
    return;
  }
  Local<Function> write_fn = info[0].As<Function>();
  std::vector<i::Handle<i::FixedArray>> heap_noise_roots;
  i::Handle<i::ByteArray> byte_array;
  uintptr_t cage_base = static_cast<uintptr_t>(i_isolate->cage_base());
  uint32_t cage_offset = 0;
  uint32_t secret = RandomUint32();
  RunSetupWithRetry(i_isolate, &heap_noise_roots, [&] {
    byte_array = i_isolate->factory()->NewByteArray(4);
    memset(byte_array->begin(), 0, 4);
    uintptr_t data_addr = reinterpret_cast<uintptr_t>(byte_array->begin());
    cage_offset = static_cast<uint32_t>(data_addr - cage_base);
  });
  Local<Value> offset_val = Number::New(isolate, static_cast<double>(cage_offset));
  Local<Value> secret_val = Integer::NewFromUnsigned(isolate, secret);
  Local<Value> argv[] = {offset_val, secret_val};
  MaybeLocal<Value> maybe_result =
      write_fn->Call(context, Undefined(isolate), 2, argv);
  if (maybe_result.IsEmpty()) {
    ReportResult("caged_write", false, "write_fn threw or returned empty");
    return;
  }
  uint32_t actual = 0;
  memcpy(&actual, byte_array->begin(), sizeof(actual));

  bool passed = (actual == secret);
  char detail[128];
  snprintf(detail, sizeof(detail),
           "secret=0x%x actual=0x%x offset=0x%lx",
           secret, actual, (unsigned long)cage_offset);
  ReportResult("caged_write", passed, detail);
}

void VerifyArbRead(const FunctionCallbackInfo<Value>& info) {
  GraderCallGuard guard;
  if (!guard.entered()) {
    ReportResult("arb_read", false, "nested grader call rejected");
    return;
  }
  if (verify_arb_read_used.exchange(true)) {
    return;
  }

  Isolate* isolate = info.GetIsolate();
  Local<Context> context = isolate->GetCurrentContext();

  if (info.Length() < 1 || !info[0]->IsFunction()) {
    ReportResult("arb_read", false, "argument must be a function");
    return;
  }
  Local<Function> read_fn = info[0].As<Function>();
  void* page = mmap_rand_page();
  if (page == MAP_FAILED) {
    ReportResult("arb_read", false, "mmap_rand_page failed");
    return;
  }
  if (!FillRandom(page, 4096)) {
    munmap(page, 4096);
    ReportResult("arb_read", false, "getrandom failed");
    return;
  }
  size_t offset = 0;
  if (!RandPageInteriorOffset(&offset)) {
    munmap(page, 4096);
    ReportResult("arb_read", false, "getrandom failed");
    return;
  }
  uint64_t secret = 0;
  memcpy(&secret, static_cast<uint8_t*>(page) + offset, sizeof(secret));

  uintptr_t target_addr = reinterpret_cast<uintptr_t>(page) + offset;
  Local<BigInt> addr_val = BigInt::NewFromUnsigned(isolate, target_addr);
  Local<Value> argv[] = {addr_val};
  MaybeLocal<Value> maybe_result =
      read_fn->Call(context, Undefined(isolate), 1, argv);
  munmap(page, 4096);

  if (maybe_result.IsEmpty()) {
    ReportResult("arb_read", false, "read_fn threw or returned empty");
    return;
  }
  Local<Value> result = maybe_result.ToLocalChecked();

  uint64_t claimed = 0;
  if (!ValueToUint64(context, result, &claimed)) {
    ReportResult("arb_read", false, "return value is not a Number or BigInt");
    return;
  }

  bool passed = (claimed == secret);
  char detail[128];
  snprintf(detail, sizeof(detail),
           "secret=0x%lx claimed=0x%lx addr=0x%lx",
           (unsigned long)secret, (unsigned long)claimed,
           (unsigned long)target_addr);
  ReportResult("arb_read", passed, detail);
}

void VerifyArbWrite(const FunctionCallbackInfo<Value>& info) {
  GraderCallGuard guard;
  if (!guard.entered()) {
    ReportResult("arb_write", false, "nested grader call rejected");
    return;
  }
  if (verify_arb_write_used.exchange(true)) {
    return;
  }

  Isolate* isolate = info.GetIsolate();
  Local<Context> context = isolate->GetCurrentContext();

  if (info.Length() < 1 || !info[0]->IsFunction()) {
    ReportResult("arb_write", false, "argument must be a function");
    return;
  }
  Local<Function> write_fn = info[0].As<Function>();
  void* page = mmap_rand_page();
  if (page == MAP_FAILED) {
    ReportResult("arb_write", false, "mmap_rand_page failed");
    return;
  }
  if (!FillRandom(page, 4096)) {
    munmap(page, 4096);
    ReportResult("arb_write", false, "getrandom failed");
    return;
  }
  uint64_t secret = 0;
  if (getrandom(&secret, sizeof(secret), 0) != sizeof(secret)) {
    munmap(page, 4096);
    ReportResult("arb_write", false, "getrandom failed");
    return;
  }
  size_t offset = 0;
  if (!RandPageInteriorOffset(&offset)) {
    munmap(page, 4096);
    ReportResult("arb_write", false, "getrandom failed");
    return;
  }

  uintptr_t target_addr = reinterpret_cast<uintptr_t>(page) + offset;
  Local<BigInt> addr_val = BigInt::NewFromUnsigned(isolate, target_addr);
  Local<BigInt> secret_val = BigInt::NewFromUnsigned(isolate, secret);
  Local<Value> argv[] = {addr_val, secret_val};
  MaybeLocal<Value> maybe_result =
      write_fn->Call(context, Undefined(isolate), 2, argv);

  if (maybe_result.IsEmpty()) {
    munmap(page, 4096);
    ReportResult("arb_write", false, "write_fn threw or returned empty");
    return;
  }
  uint64_t actual = *reinterpret_cast<uint64_t*>(
      static_cast<uint8_t*>(page) + offset);
  munmap(page, 4096);

  bool passed = (actual == secret);
  char detail[128];
  snprintf(detail, sizeof(detail),
           "secret=0x%lx actual=0x%lx addr=0x%lx",
           (unsigned long)secret, (unsigned long)actual,
           (unsigned long)target_addr);
  ReportResult("arb_write", passed, detail);
}

namespace {

static std::atomic<bool> g_proc_snapshot_done{false};

uint64_t SnapshotLowestBase(const char* needle) {
  FILE* f = fopen("/proc/self/maps", "r");
  if (f == nullptr) return 0;

  uint64_t lowest = 0;
  char line[512];
  while (fgets(line, sizeof(line), f) != nullptr) {
    if (strstr(line, needle) == nullptr) continue;
    uint64_t base = strtoull(line, nullptr, 16);
    if (lowest == 0 || base < lowest) lowest = base;
  }
  fclose(f);
  return lowest;
}

}  // namespace

void InitProcSnapshot() {
  if (g_proc_snapshot_done.exchange(true)) return;
  // Snapshot the base addresses we need before SealGraderBaseline and
  // before PR_SET_DUMPABLE=0 takes effect.
  g_baseline.binary_base = SnapshotLowestBase("/d8");
  g_baseline.libc_base   = SnapshotLowestBase("libc");
  prctl(PR_SET_DUMPABLE, 0, 0, 0, 0);
}

void VerifyInfoleak(const FunctionCallbackInfo<Value>& info) {
  Isolate* isolate = info.GetIsolate();
  Local<Context> context = isolate->GetCurrentContext();

  if (info.Length() < 2) {
    ReportResult("infoleak", false, "expected 2 arguments: type_str, claimed_addr");
    return;
  }
  if (!info[0]->IsString()) {
    ReportResult("infoleak", false, "first argument must be a string");
    return;
  }
  String::Utf8Value type_utf8(isolate, info[0]);
  const char* type_str = *type_utf8;
  if (type_str == nullptr) {
    ReportResult("infoleak", false, "failed to read type string");
    return;
  }
  std::atomic<bool>* guard = nullptr;
  const char* report_key = nullptr;
  if (strcmp(type_str, "binary") == 0) {
    guard = &verify_infoleak_binary_used;
    report_key = "infoleak_binary";
  } else if (strcmp(type_str, "libc") == 0) {
    guard = &verify_infoleak_libc_used;
    report_key = "infoleak_libc";
  } else if (strcmp(type_str, "stack") == 0) {
    guard = &verify_infoleak_stack_used;
    report_key = "infoleak_stack";
  } else {
    ReportResult("infoleak", false, "type must be 'binary', 'libc', or 'stack'");
    return;
  }
  if (guard->exchange(true)) {
    return;
  }
  uint64_t claimed = 0;
  if (!ValueToUint64(context, info[1], &claimed)) {
    ReportResult(report_key, false, "claimed_addr is not a Number or BigInt");
    return;
  }
  uint64_t claimed_page = claimed & ~0xFFFULL;

  uint64_t expected_page = 0;

  if (strcmp(type_str, "stack") == 0) {
    uintptr_t stack_local;
    uintptr_t stack_addr = (uintptr_t)&stack_local;
    expected_page = stack_addr & ~0xFFFULL;
  } else {
    uint64_t snapshot = (strcmp(type_str, "binary") == 0)
                            ? g_baseline.binary_base : g_baseline.libc_base;
    if (snapshot == 0) {
      char detail[128];
      snprintf(detail, sizeof(detail),
               "no snapshot for '%s'", type_str);
      ReportResult(report_key, false, detail);
      return;
    }
    expected_page = snapshot & ~0xFFFULL;
  }

  bool passed = (claimed_page == expected_page);
  char detail[128];
  snprintf(detail, sizeof(detail),
           "claimed_page=0x%lx expected_page=0x%lx",
           (unsigned long)claimed_page, (unsigned long)expected_page);
  ReportResult(report_key, passed, detail);
}

namespace {

struct alignas(4096) PCStorage {
  uintptr_t target_page;
  struct sigaction prev_segv;
  struct sigaction prev_bus;
  struct sigaction prev_ill;
  uint8_t pad[4096 - sizeof(uintptr_t) - 3 * sizeof(struct sigaction)];
};
static_assert(sizeof(PCStorage) == 4096, "PCStorage must occupy exactly one page");

alignas(4096) static PCStorage g_pc_storage;
static_assert(alignof(PCStorage) == 4096, "g_pc_storage must be page-aligned");

alignas(16) static uint8_t g_sig_stack[SIGSTKSZ * 2];
static std::atomic<bool> g_pc_init_done{false};

static const struct sigaction* PrevSigaction(int sig) {
  switch (sig) {
    case SIGSEGV: return &g_pc_storage.prev_segv;
    case SIGBUS:  return &g_pc_storage.prev_bus;
    case SIGILL:  return &g_pc_storage.prev_ill;
    default:      return nullptr;
  }
}

void ChainOrExit(int sig, siginfo_t* info, void* uctx_raw, uintptr_t rip,
                 uintptr_t target) {
  const struct sigaction* prev = PrevSigaction(sig);
  if (prev != nullptr) {
    if (prev->sa_flags & SA_SIGINFO) {
      if (prev->sa_sigaction != nullptr) {
        prev->sa_sigaction(sig, info, uctx_raw);
        return;
      }
    } else {
      void (*h)(int) = prev->sa_handler;
      if (h != SIG_DFL && h != SIG_IGN && h != nullptr) {
        h(sig);
        return;
      }
    }
  }
  char detail[128];
  snprintf(detail, sizeof(detail),
           "rip=0x%lx target=0x%lx sig=%d",
           static_cast<unsigned long>(rip),
           static_cast<unsigned long>(target), sig);
  ReportResult("pc_control", false, detail);
  FinishGraderACE();
  _exit(139);
}

// Async-signal-safe: prctl + snprintf + write(2) only.
void PCSignalHandler(int sig, siginfo_t* info, void* uctx_raw) {
  ucontext_t* uc = static_cast<ucontext_t*>(uctx_raw);
#if defined(__x86_64__)
  uintptr_t rip = static_cast<uintptr_t>(uc->uc_mcontext.gregs[REG_RIP]);
#elif defined(__aarch64__)
  uintptr_t rip = static_cast<uintptr_t>(uc->uc_mcontext.pc);
#else
  uintptr_t rip = 0;
#endif
  uintptr_t target = g_pc_storage.target_page;
  uintptr_t fault_page =
      reinterpret_cast<uintptr_t>(info->si_addr) & ~0xFFFULL;

  if (target != 0 && rip == target && fault_page == target &&
      info->si_code == SEGV_ACCERR) {
    char detail[128];
    snprintf(detail, sizeof(detail),
             "rip=0x%lx target=0x%lx sig=%d",
             static_cast<unsigned long>(rip),
             static_cast<unsigned long>(target), sig);
    ReportResult("pc_control", true, detail);
    FinishGraderACE();
    _exit(139);
  }

  ChainOrExit(sig, info, uctx_raw, rip, target);
}

}  // namespace

// Must be called before v8::V8::Initialize() — V8 allocates MPK keys during
// initialization, so the seccomp filter has to be installed first.
void InitMpkSeccomp() {
  static std::atomic<bool> done{false};
  if (done.exchange(true)) return;

  const char* env = getenv("GRADER_DISABLE_MPK");
  bool disable_mpk = (env == nullptr) || (strcmp(env, "0") != 0);
  if (!disable_mpk) return;

  // PR_SET_NO_NEW_PRIVS is required for unprivileged seccomp filter install.
  prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0);

  struct sock_filter filter[] = {
      BPF_STMT(BPF_LD | BPF_W | BPF_ABS,
               offsetof(struct seccomp_data, nr)),
      BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_pkey_alloc, 0, 1),
      BPF_STMT(BPF_RET | BPF_K,
               SECCOMP_RET_ERRNO | (ENOSPC & SECCOMP_RET_DATA)),
      BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
  };
  struct sock_fprog prog = {
      .len = static_cast<unsigned short>(sizeof(filter) / sizeof(filter[0])),
      .filter = filter,
  };
  syscall(__NR_seccomp, SECCOMP_SET_MODE_FILTER, 0, &prog);
}

void InitPCControl() {
  if (g_pc_init_done.exchange(true)) return;

  void* page = mmap_rand_page_prot(PROT_NONE);
  g_pc_storage.target_page =
      (page == MAP_FAILED) ? 0 : reinterpret_cast<uintptr_t>(page);

  // Alternate signal stack so the handler runs even with corrupted RSP.
  stack_t ss = {};
  ss.ss_sp = g_sig_stack;
  ss.ss_size = sizeof(g_sig_stack);
  ss.ss_flags = 0;
  sigaltstack(&ss, nullptr);

  // Must run after V8::Initialize() so prev_* captures V8's WASM trap handler.
  struct sigaction sa = {};
  sa.sa_sigaction = PCSignalHandler;
  sa.sa_flags = SA_SIGINFO | SA_ONSTACK;
  sigemptyset(&sa.sa_mask);
  sigaction(SIGSEGV, &sa, &g_pc_storage.prev_segv);
  sigaction(SIGBUS, &sa, &g_pc_storage.prev_bus);
  sigaction(SIGILL, &sa, &g_pc_storage.prev_ill);

  mprotect(&g_pc_storage, sizeof(g_pc_storage), PROT_READ);
}

void GetPCTarget(const FunctionCallbackInfo<Value>& info) {
  Isolate* isolate = info.GetIsolate();

  uintptr_t target = g_pc_storage.target_page;
  if (target == 0) {
    info.GetReturnValue().SetUndefined();
    return;
  }

  Local<BigInt> result =
      BigInt::NewFromUnsigned(isolate, static_cast<uint64_t>(target));
  info.GetReturnValue().Set(result);
}

void GetACEName(const FunctionCallbackInfo<Value>& info) {
  Isolate* isolate = info.GetIsolate();

  if (g_baseline.ace_expected[0] == '\0') {
    info.GetReturnValue().SetUndefined();
    return;
  }

  info.GetReturnValue().Set(
      String::NewFromUtf8(isolate, g_baseline.ace_expected).ToLocalChecked());
}

namespace {

static const char kWorkspacePrefix[] = "/rlenv/workspace/";
constexpr size_t kWorkspacePrefixLen = sizeof(kWorkspacePrefix) - 1;

}  // namespace

void InitGraderFileGate() {
  if (g_grader_filegate_done.exchange(true)) return;
  struct stat st;
  if (stat(kWorkspacePrefix, &st) == 0) {
    g_baseline.workspace_dev = st.st_dev;
  }
}

// Caches the grader env vars into g_baseline at init so subsequent reads
// don't rely on live getenv. Must run before SealGraderBaseline.
void InitGraderEnvCache() {
  if (g_grader_envcache_done.exchange(true)) return;

  g_baseline.result_fd = -1;
  const char* fd_env = getenv("GRADER_RESULT_FD");
  if (fd_env != nullptr) {
    g_baseline.result_fd = atoi(fd_env);
  }

  g_baseline.ace_expected[0] = '\0';
  const char* ace_env = getenv("GRADER_ACE_NAME");
  if (ace_env != nullptr) {
    // sizeof(g_baseline.ace_expected) is 16; prctl(PR_GET_NAME) writes at
    // most 16 bytes including the trailing NUL, so we mirror that cap here.
    strncpy(g_baseline.ace_expected, ace_env,
            sizeof(g_baseline.ace_expected) - 1);
    g_baseline.ace_expected[sizeof(g_baseline.ace_expected) - 1] = '\0';
  }
}

// Mprotects the GraderBaseline page PROT_READ. Aborts on mprotect failure;
// a writable baseline is worse than not starting at all. Must be called
// last in the grader init sequence — any subsequent write to g_baseline
// will SIGSEGV.
void SealGraderBaseline() {
  if (g_grader_baseline_sealed.exchange(true)) return;
  if (mprotect(&g_baseline, sizeof(g_baseline), PROT_READ) != 0) {
    fprintf(stderr,
            "SealGraderBaseline: mprotect failed: %s\n", strerror(errno));
    _exit(143);
  }
}

namespace {

class GraderMappedFile final : public base::OS::MemoryMappedFile {
 public:
  GraderMappedFile(void* memory, size_t size)
      : memory_(memory), size_(size) {}
  ~GraderMappedFile() override {
    if (memory_ != nullptr && size_ != 0) {
      munmap(memory_, size_);
    }
  }
  void* memory() const override { return memory_; }
  size_t size() const override { return size_; }

 private:
  void* memory_;
  size_t size_;
};

}  // namespace

base::OS::MemoryMappedFile* GraderOpenAndMap(const char* name) {
  int fd = GraderOpenWorkspaceFile(name);
  if (fd < 0) return nullptr;

  struct stat st;
  if (fstat(fd, &st) < 0) {
    close(fd);
    return nullptr;
  }
  if (st.st_size == 0) {
    close(fd);
    return new GraderMappedFile(nullptr, 0);
  }

  void* mem = mmap(nullptr, static_cast<size_t>(st.st_size), PROT_READ,
                   MAP_PRIVATE, fd, 0);
  close(fd);
  if (mem == MAP_FAILED) return nullptr;
  return new GraderMappedFile(mem, static_cast<size_t>(st.st_size));
}

int GraderOpenWorkspaceFile(const char* name) {
  if (name == nullptr) return -1;

  int fd = open(name, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
  if (fd < 0) return -1;

  char fdpath[64];
  int n = snprintf(fdpath, sizeof(fdpath), "/proc/self/fd/%d", fd);
  if (n <= 0 || (size_t)n >= sizeof(fdpath)) {
    close(fd);
    return -1;
  }

  char canonical[PATH_MAX];
  ssize_t r = readlink(fdpath, canonical, sizeof(canonical) - 1);
  if (r < 0) {
    close(fd);
    return -1;
  }
  canonical[r] = '\0';

  if (strncmp(canonical, kWorkspacePrefix, kWorkspacePrefixLen) != 0) {
    close(fd);
    return -1;
  }

  struct stat st;
  if (fstat(fd, &st) < 0 || !S_ISREG(st.st_mode)) {
    close(fd);
    return -1;
  }

  return fd;
}

// Async-signal-safe: prctl + snprintf + write(2) only. Idempotent so the
// shutdown hook and PCSignalHandler can both call without duplicating output.
void FinishGraderACE() {
  static std::atomic<bool> done{false};
  if (done.exchange(true)) return;

  if (g_baseline.ace_expected[0] == '\0') {
    return;
  }

  char comm1[16] = {0};
  char comm2[16] = {0};
  int rc = prctl(PR_GET_NAME, comm1, 0, 0, 0);
  if (rc != 0) {
    ReportResult("ace", false, "prctl(PR_GET_NAME) failed");
    return;
  }
  __asm__ __volatile__("" ::: "memory");
  rc = prctl(PR_GET_NAME, comm2, 0, 0, 0);
  if (rc != 0) {
    ReportResult("ace", false, "prctl(PR_GET_NAME) failed");
    return;
  }
  // strcmp-style compare; PR_GET_NAME doesn't zero-pad past the null so
  // bytes after it can legitimately vary call-to-call.
  for (size_t i = 0; i < sizeof(comm1); i++) {
    if (comm1[i] != comm2[i]) {
      ReportResult("ace", false, "comm changed between reads");
      return;
    }
    if (comm1[i] == '\0') break;
  }
  comm1[15] = '\0';

  bool passed = (strcmp(comm1, g_baseline.ace_expected) == 0);
  char detail[128];
  snprintf(detail, sizeof(detail), "got=%s", comm1);
  ReportResult("ace", passed, detail);
}

}  // namespace v8
