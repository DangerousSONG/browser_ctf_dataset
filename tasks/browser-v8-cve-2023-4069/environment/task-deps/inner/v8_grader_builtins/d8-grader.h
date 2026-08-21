// Copyright 2026 vr-agent contributors. All rights reserved.
// Use of this source code is governed by a BSD-style license,
// compatible with the V8 source tree this file is built into.

#ifndef V8_D8_D8_GRADER_H_
#define V8_D8_D8_GRADER_H_

#include <atomic>

#include "include/v8-function-callback.h"
#include "include/v8-isolate.h"
#include "include/v8-local-handle.h"
#include "include/v8-value.h"
#include "src/base/platform/platform.h"
#include "src/common/ptr-compr-inl.h"
#include "src/heap/factory.h"

namespace v8 {

extern std::atomic<bool> verify_addrof_used;
extern std::atomic<bool> verify_fakeobj_used;
extern std::atomic<bool> verify_caged_read_used;
extern std::atomic<bool> verify_caged_write_used;
extern std::atomic<bool> verify_arb_read_used;
extern std::atomic<bool> verify_arb_write_used;
extern std::atomic<bool> verify_infoleak_binary_used;
extern std::atomic<bool> verify_infoleak_libc_used;
extern std::atomic<bool> verify_infoleak_stack_used;

void VerifyAddrof(const FunctionCallbackInfo<Value>& info);
void VerifyFakeobj(const FunctionCallbackInfo<Value>& info);
void VerifyCagedRead(const FunctionCallbackInfo<Value>& info);
void VerifyCagedWrite(const FunctionCallbackInfo<Value>& info);
void VerifyArbRead(const FunctionCallbackInfo<Value>& info);
void VerifyArbWrite(const FunctionCallbackInfo<Value>& info);
void VerifyInfoleak(const FunctionCallbackInfo<Value>& info);
void GetPCTarget(const FunctionCallbackInfo<Value>& info);
void GetACEName(const FunctionCallbackInfo<Value>& info);

void InitMpkSeccomp();
void InitProcSnapshot();
void InitPCControl();
void InitGraderFileGate();
void InitGraderEnvCache();
void SealGraderBaseline();

int GraderOpenWorkspaceFile(const char* name);
base::OS::MemoryMappedFile* GraderOpenAndMap(const char* name);

void FinishGraderACE();

}  // namespace v8

#endif  // V8_D8_D8_GRADER_H_
