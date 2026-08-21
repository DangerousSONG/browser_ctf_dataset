#!/usr/bin/env python3
# Copyright 2026 bench-v8 contributors. All rights reserved.
# Use of this source code is governed by a BSD-style license,
# compatible with the V8 source tree this file is built into.
"""Apply d8 grader integration via textual anchors. Run from v8 source root."""
import sys
from pathlib import Path


def edit(path: str, old: str, new: str) -> None:
    p = Path(path)
    src = p.read_text()
    n = src.count(old)
    if n != 1:
        sys.exit(f"{path}: anchor matched {n} times (expected 1):\n{old}")
    p.write_text(src.replace(old, new, 1))


edit(
    "BUILD.gn",
    '    "src/d8/d8-console.cc",\n'
    '    "src/d8/d8-console.h",\n',
    '    "src/d8/d8-console.cc",\n'
    '    "src/d8/d8-console.h",\n'
    '    "src/d8/d8-grader.cc",\n'
    '    "src/d8/d8-grader.h",\n',
)

edit(
    "src/d8/d8.cc",
    '#include "src/d8/d8-console.h"\n',
    '#include "src/d8/d8-console.h"\n'
    '#include "src/d8/d8-grader.h"\n',
)

edit(
    "src/d8/d8.cc",
    '  if (!i::v8_flags.fuzzing) {\n'
    '    global_template->Set(isolate, "writeFile",\n'
    '                         FunctionTemplate::New(isolate, WriteFile));\n'
    '  }\n',
    '  if (!i::v8_flags.fuzzing && !options.grader) {\n'
    '    global_template->Set(isolate, "writeFile",\n'
    '                         FunctionTemplate::New(isolate, WriteFile));\n'
    '  }\n',
)

edit(
    "src/d8/d8.cc",
    '  global_template->Set(isolate, "read",\n'
    '                       FunctionTemplate::New(isolate, ReadFile));\n'
    '  global_template->Set(isolate, "readbuffer",\n'
    '                       FunctionTemplate::New(isolate, ReadBuffer));\n'
    '  global_template->Set(isolate, "readline",\n'
    '                       FunctionTemplate::New(isolate, ReadLine));\n'
    '  global_template->Set(isolate, "load",\n'
    '                       FunctionTemplate::New(isolate, ExecuteFile));\n',
    '  if (!options.grader) {\n'
    '    global_template->Set(isolate, "read",\n'
    '                         FunctionTemplate::New(isolate, ReadFile));\n'
    '    global_template->Set(isolate, "readbuffer",\n'
    '                         FunctionTemplate::New(isolate, ReadBuffer));\n'
    '    global_template->Set(isolate, "readline",\n'
    '                         FunctionTemplate::New(isolate, ReadLine));\n'
    '    global_template->Set(isolate, "load",\n'
    '                         FunctionTemplate::New(isolate, ExecuteFile));\n'
    '  }\n',
)

edit(
    "src/d8/d8.cc",
    '  if (!i::v8_flags.fuzzing) {\n'
    '    global_template->Set(isolate, "os", Shell::CreateOSTemplate(isolate));\n'
    '  }\n',
    '  if (!i::v8_flags.fuzzing && !options.grader) {\n'
    '    global_template->Set(isolate, "os", Shell::CreateOSTemplate(isolate));\n'
    '  }\n',
)

edit(
    "src/d8/d8.cc",
    '  global_template->Set(isolate, "d8", Shell::CreateD8Template(isolate));\n',
    '  if (!options.grader) {\n'
    '    global_template->Set(isolate, "d8", Shell::CreateD8Template(isolate));\n'
    '  }\n',
)

d8cc_src = Path("src/d8/d8.cc").read_text()
if 'global_template->Set(isolate, "testRunner",' in d8cc_src:
    edit(
        "src/d8/d8.cc",
        '  global_template->Set(isolate, "testRunner",\n'
        '                       Shell::CreateTestRunnerTemplate(isolate));\n',
        '  if (!options.grader) {\n'
        '    global_template->Set(isolate, "testRunner",\n'
        '                         Shell::CreateTestRunnerTemplate(isolate));\n'
        '  }\n',
    )

# Long anchor avoids spanning the optional #ifdef V8_FUZZILLI block.
edit(
    "src/d8/d8.cc",
    '  if (i::v8_flags.expose_async_hooks) {\n'
    '    global_template->Set(isolate, "async_hooks",\n'
    '                         Shell::CreateAsyncHookTemplate(isolate));\n'
    '  }\n'
    '\n'
    '  return global_template;\n',
    '  if (i::v8_flags.expose_async_hooks) {\n'
    '    global_template->Set(isolate, "async_hooks",\n'
    '                         Shell::CreateAsyncHookTemplate(isolate));\n'
    '  }\n'
    '\n'
    '  if (options.grader) {\n'
    '    global_template->Set(isolate, "__graderVerifyAddrof",\n'
    '                         FunctionTemplate::New(isolate, VerifyAddrof));\n'
    '    global_template->Set(isolate, "__graderVerifyFakeobj",\n'
    '                         FunctionTemplate::New(isolate, VerifyFakeobj));\n'
    '    global_template->Set(isolate, "__graderVerifyCagedRead",\n'
    '                         FunctionTemplate::New(isolate, VerifyCagedRead));\n'
    '    global_template->Set(isolate, "__graderVerifyCagedWrite",\n'
    '                         FunctionTemplate::New(isolate, VerifyCagedWrite));\n'
    '    global_template->Set(isolate, "__graderVerifyArbRead",\n'
    '                         FunctionTemplate::New(isolate, VerifyArbRead));\n'
    '    global_template->Set(isolate, "__graderVerifyArbWrite",\n'
    '                         FunctionTemplate::New(isolate, VerifyArbWrite));\n'
    '    global_template->Set(isolate, "__graderVerifyInfoleak",\n'
    '                         FunctionTemplate::New(isolate, VerifyInfoleak));\n'
    '    global_template->Set(isolate, "__graderGetPCTarget",\n'
    '                         FunctionTemplate::New(isolate, GetPCTarget));\n'
    '    global_template->Set(isolate, "__graderGetACEName",\n'
    '                         FunctionTemplate::New(isolate, GetACEName));\n'
    '    InitGraderFileGate();\n'
    '    InitProcSnapshot();\n'
    '    InitGraderEnvCache();\n'
    '    InitPCControl();\n'
    '    SealGraderBaseline();\n'
    '  }\n'
    '\n'
    '  return global_template;\n',
)

# ReadFileData was extracted as a separate helper in 2024-09 (V8 fbb9dffab10
# "Static source phase import").  Earlier V8s call MemoryMappedFile::open
# directly from the lower-level ReadFile overload.  Pick the form present.
d8cc_src = Path("src/d8/d8.cc").read_text()
if "Shell::ReadFileData(" in d8cc_src:
    edit(
        "src/d8/d8.cc",
        'std::unique_ptr<base::OS::MemoryMappedFile> Shell::ReadFileData(\n'
        '    Isolate* isolate, const char* name, bool should_throw) {\n'
        '  std::unique_ptr<base::OS::MemoryMappedFile> file(\n'
        '      base::OS::MemoryMappedFile::open(\n'
        '          name, base::OS::MemoryMappedFile::FileMode::kReadOnly));\n',
        'std::unique_ptr<base::OS::MemoryMappedFile> Shell::ReadFileData(\n'
        '    Isolate* isolate, const char* name, bool should_throw) {\n'
        '  std::unique_ptr<base::OS::MemoryMappedFile> file(\n'
        '      options.grader\n'
        '          ? v8::GraderOpenAndMap(name)\n'
        '          : base::OS::MemoryMappedFile::open(\n'
        '                name, base::OS::MemoryMappedFile::FileMode::kReadOnly));\n',
    )
else:
    edit(
        "src/d8/d8.cc",
        'MaybeLocal<String> Shell::ReadFile(Isolate* isolate, const char* name,\n'
        '                                   bool should_throw) {\n'
        '  std::unique_ptr<base::OS::MemoryMappedFile> file(\n'
        '      base::OS::MemoryMappedFile::open(\n'
        '          name, base::OS::MemoryMappedFile::FileMode::kReadOnly));\n',
        'MaybeLocal<String> Shell::ReadFile(Isolate* isolate, const char* name,\n'
        '                                   bool should_throw) {\n'
        '  std::unique_ptr<base::OS::MemoryMappedFile> file(\n'
        '      options.grader\n'
        '          ? v8::GraderOpenAndMap(name)\n'
        '          : base::OS::MemoryMappedFile::open(\n'
        '                name, base::OS::MemoryMappedFile::FileMode::kReadOnly));\n',
    )

edit(
    "src/d8/d8.cc",
    '  OnExit(isolate, true);\n',
    '  if (options.grader) {\n'
    '    v8::FinishGraderACE();\n'
    '  }\n'
    '  OnExit(isolate, true);\n',
)

# Drop the V8 CPU-profiler entry points in --grader mode. They are not
# needed for grading and are removed for consistency with other d8-shell
# surfaces that are off under --grader.
edit(
    "src/d8/d8-console.cc",
    'void D8Console::Profile(const debug::ConsoleCallArguments& args,\n'
    '                        const v8::debug::ConsoleContext&) {\n'
    '  if (!profiler_) {\n',
    'void D8Console::Profile(const debug::ConsoleCallArguments& args,\n'
    '                        const v8::debug::ConsoleContext&) {\n'
    '  if (Shell::options.grader) return;\n'
    '  if (!profiler_) {\n',
)
edit(
    "src/d8/d8-console.cc",
    'void D8Console::ProfileEnd(const debug::ConsoleCallArguments& args,\n'
    '                           const v8::debug::ConsoleContext&) {\n'
    '  if (!profiler_) return;\n',
    'void D8Console::ProfileEnd(const debug::ConsoleCallArguments& args,\n'
    '                           const v8::debug::ConsoleContext&) {\n'
    '  if (Shell::options.grader) return;\n'
    '  if (!profiler_) return;\n',
)

# v8 has two flag-parse styles; detect and match.
d8cc = Path("src/d8/d8.cc").read_text()
if 'FlagMatches("--omit-quit"' in d8cc:
    edit(
        "src/d8/d8.cc",
        '    } else if (FlagMatches("--omit-quit", &argv[i])) {\n'
        '      options.omit_quit = true;\n'
        '    } else if (FlagMatches("--no-wait-for-background-tasks"',
        '    } else if (FlagMatches("--omit-quit", &argv[i])) {\n'
        '      options.omit_quit = true;\n'
        '    } else if (FlagMatches("--grader", &argv[i])) {\n'
        '      options.grader = true;\n'
        '    } else if (FlagMatches("--no-wait-for-background-tasks"',
    )
elif 'strcmp(argv[i], "--omit-quit")' in d8cc:
    edit(
        "src/d8/d8.cc",
        '    } else if (strcmp(argv[i], "--omit-quit") == 0) {\n'
        '      options.omit_quit = true;\n'
        '      argv[i] = nullptr;\n'
        '    } else if (strcmp(argv[i], "--no-wait-for-background-tasks")',
        '    } else if (strcmp(argv[i], "--omit-quit") == 0) {\n'
        '      options.omit_quit = true;\n'
        '      argv[i] = nullptr;\n'
        '    } else if (strcmp(argv[i], "--grader") == 0) {\n'
        '      options.grader = true;\n'
        '      argv[i] = nullptr;\n'
        '    } else if (strcmp(argv[i], "--no-wait-for-background-tasks")',
    )
else:
    sys.exit("src/d8/d8.cc: could not detect --omit-quit handler style")

edit(
    "src/d8/d8.h",
    '  DisallowReassignment<bool> omit_quit = {"omit-quit", false};\n',
    '  DisallowReassignment<bool> omit_quit = {"omit-quit", false};\n'
    '  DisallowReassignment<bool> grader = {"grader", false};\n',
)

# Earliest-available anchor; both V8 12.x (ThreadIsolatedAllocator) and 13.0+
# (SandboxHardwareSupport) call pkey_alloc before user code runs.
d8cc_src = Path("src/d8/d8.cc").read_text()
if "SandboxHardwareSupport::InitializeBeforeThreadCreation" in d8cc_src:
    edit(
        "src/d8/d8.cc",
        '  v8::SandboxHardwareSupport::InitializeBeforeThreadCreation();\n',
        '  if (options.grader) {\n'
        '    v8::InitMpkSeccomp();\n'
        '  }\n'
        '  v8::SandboxHardwareSupport::InitializeBeforeThreadCreation();\n',
    )
else:
    edit(
        "src/d8/d8.cc",
        '  platform::tracing::TracingController* tracing_controller = tracing.get();\n',
        '  if (options.grader) {\n'
        '    v8::InitMpkSeccomp();\n'
        '  }\n'
        '  platform::tracing::TracingController* tracing_controller = tracing.get();\n',
    )

print("grader integration applied.")
