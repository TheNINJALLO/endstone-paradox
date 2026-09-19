# Native build

Target: x86-64 Endstone 0.11.11, BDS 1.26.51.1, protocol 2193. Use LLVM/Clang 20, C++23, CMake 3.29+, Ninja, Git, Python 3.12+ and uv. Linux must use libc++ rather than libstdc++ to match Endstone's C++ ABI. Windows uses clang-cl with the Visual Studio 2022 SDK and dynamic MSVC runtime.

## Linux

Install Clang 20, libc++20, libc++abi20 and OpenSSL 3 development headers. The [pinned remote-dev environment](references.lock.json) documents Endstone's LLVM/libc++ setup; the plugin needs no SSH server or mounted SSH keys.

```sh
python -m pip install cmake==3.31.6 ninja uv==0.12.17
cmake -S . -B build/linux -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=clang-20 -DCMAKE_CXX_COMPILER=clang++-20
cmake --build build/linux --parallel 4
ctest --test-dir build/linux --output-on-failure
python native/tools/package.py build/linux/endstone_paradox.so --platform linux
```

## Windows

Install VS 2022 C++ Build Tools, LLVM 20.1.8, Python 3.12+ and Git. Run in a VS developer shell, or let the helper initialize one.

```powershell
python -m pip install cmake==3.31.6 ninja conan==2.31.0 uv==0.12.17
conan profile detect --name paradox-native
conan install --requires=openssl/3.5.2 --output-folder=build/deps -pr:h=paradox-native -pr:b=paradox-native -s build_type=Release -g CMakeDeps --build=missing
powershell -NoProfile -ExecutionPolicy Bypass -File native/tools/build-windows.ps1 -LlvmRoot 'C:/Program Files/LLVM' -DependencyDirectory "$PWD/build/deps"
python native/tools/package.py build/windows/endstone_paradox.dll --platform windows
```

The process-only execution-policy option does not change machine policy. CMake fetches pinned source revisions and applies `harden_protocol.py` before code generation. The first build generates/compiles the complete protocol library and takes several minutes. The Windows helper may reuse explicitly available scratch reference/generated trees used during validation; ordinary clean checkouts fetch and generate the same pinned dependency.

## Server verification and smoke test

```sh
python native/tools/verify-server.py bedrock-server-linux-1.26.51.1.zip --platform linux
python native/tools/verify-server.py bedrock-server-windows-1.26.51.1.zip --platform windows
```

`native/tools/smoke-server.py` accepts an **isolated extracted server folder**, plugin binary and output directory. It overwrites that disposable server's properties/configuration, uses dedicated ports, disables external Paradox integrations, tests native loading and authenticated HTTP commands, then stops the server. Run it with the Python interpreter from an Endstone 0.11.11 environment. It refuses paths outside a directory named `scratch` or `/runtime/` and must not be pointed at production data. Windows uses a hidden process and Endstone's official DLL-injection bootstrap. No gameplay client is connected by this test.

## Dependency and ABI notes

Endstone and bedrock-protocol are pinned by full commit. JSON/SQLite archives are pinned by SHA-256; toml++ and cpp-httplib by full commit. OpenSSL uses platform OpenSSL 3 on Linux and the declared Conan package on Windows. All linked third-party license texts ship with the package.

Endstone's plugin factory export, public C++ headers, event callbacks, scheduler, ItemStack/NBT API and native packet hooks form the ABI boundary. Packet structures are decoded values, not reinterpret-casts of BDS memory. There are no guessed offsets or private vtable calls. A new BDS/protocol needs its own schema/ABI review; unknown versions disable packet inspection and retain management functions.
