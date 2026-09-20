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

## Connected-client acceptance tests

The additional harness uses two offline scripted clients built from the pinned Go module in `native/tests/bedrock-client` (Go 1.26.8, gophertunnel v1.62.0, protocol 2193). These clients complete the spawn and loading-screen handshakes and send real movement, command, inventory, combat and form-response packets to BDS. Combat must produce a server health update to pass; sending an attack packet alone is insufficient. They are not a replacement for retail controller/touch/physics testing.

1. Use a disposable server directory and an Endstone 0.11.11 Python environment. Run `acceptance-server.py SERVER PLUGIN OUTPUT --seconds 2400` and wait for `OUTPUT/ready.json`. The runner replaces only the disposable server configuration, disables Paradox's external integrations, creates a separate arena world, and enables offline LAN discovery. Keep the test server on an isolated network.
2. Build the helper with `go build -o /work/scratch/validation/bedrock-client .` from `native/tests/bedrock-client` in a dedicated Linux client container. Mount this checkout at `/work`; install `iproute2`; grant `NET_ADMIN` only to this test container. No host network or production container should be used. The validation run used `golang:1.26.8-bookworm` with digest `sha256:a688600ca24f8a4d3ca77f95b0dd40704a9fc787c826660eb7ba0b641b8b175d`.
3. Run `python native/tools/network-acceptance.py OUTPUT --server-container SERVER_CONTAINER --server-path /runtime/paradox --client-container CLIENT_CONTAINER --address SERVER_IP:39301`. For a Windows server, use `--server-container=` and its absolute scratch directory as `--server-path`. Windows and Linux runs need separate client containers if run concurrently.
4. Inspect `network-results.json`, `network-samples.ndjson`, `client.log` and `server.log`. Every required check must pass. The Linux server stall test verifies the executable path before stopping only the owned BDS process for two seconds, then resumes it in a `finally` block.
5. Create `OUTPUT/stop` to stop BDS gracefully. Stop the dedicated client containers when finished. The runner restores their network delay in cleanup; it does not change host firewall or network settings.

The client targets an explicit unicast discovery address and matches both test server/world names. BDS advertises discovery v7, so the helper matches those labels without using the library's older v6 metadata decoder. A 30 ms client network delay provides measurable RTT: localhost's rounded-zero ping intentionally leaves Paradox's health gate closed and cannot prove active detection.

## Dependency and ABI notes

Endstone and bedrock-protocol are pinned by full commit. JSON/SQLite archives are pinned by SHA-256; toml++ and cpp-httplib by full commit. OpenSSL uses platform OpenSSL 3 on Linux and the declared Conan package on Windows. All linked third-party license texts ship with the package.

Endstone's plugin factory export, public C++ headers, event callbacks, scheduler, ItemStack/NBT API and native packet hooks form the ABI boundary. Packet structures are decoded values, not reinterpret-casts of BDS memory. There are no guessed offsets or private vtable calls. A new BDS/protocol needs its own schema/ABI review; unknown versions disable packet inspection and retain management functions.
