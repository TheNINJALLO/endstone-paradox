# Third-party notices

Paradox is GPL-3.0-or-later; the root LICENSE applies to its native code. This directory contains notices for Endstone 0.11.11 (Apache-2.0), bedrock-protocol 0.3.0 (MIT, modified bounded inspection), nlohmann/json 3.12.0 (MIT), toml++ 3.4.0 (MIT), cpp-httplib 0.20.1 (MIT), expected-lite 0.8.0 (Boost-1.0), SQLite 3.50.4 (public domain), OpenSSL 3.5.2 (Apache-2.0), zlib 1.3.2 and LLVM/libc++20 (Apache-2.0 with LLVM exceptions and included notices).

Linux uses the system OpenSSL 3 libraries and links libc++/libc++abi statically according to Endstone's native build setup. The Windows build links the declared OpenSSL/zlib packages and uses the MSVC runtime supplied for Endstone. No Minecraft server binaries, assets or private debugging symbols are distributed.
