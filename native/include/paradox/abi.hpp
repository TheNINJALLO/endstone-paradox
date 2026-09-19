// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <endstone/version.h>
#include <string>
#include <string_view>

// Endstone owns the BDS detours and translates its private server ABI into the
// public native API. Reject incompatible plugin ABIs at build time. No class
// layout or packet wire layout is inferred from a reinterpret_cast.
static_assert(sizeof(void *) == 8, "Paradox targets the x86-64 BDS runtime");
static_assert(std::string_view(ENDSTONE_API_VERSION) == "0.11", "Review a new Endstone ABI before upgrading");
#if defined(_WIN32)
static_assert(sizeof(std::string) == 32, "Use the matching release MSVC C++ runtime");
#elif defined(_LIBCPP_VERSION)
static_assert(sizeof(std::string) == 24, "Use Endstone's libc++ ABI");
#else
#error "Linux Paradox must be built with libc++ to match Endstone"
#endif
