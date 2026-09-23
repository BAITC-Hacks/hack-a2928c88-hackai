ERROR: logging before google.Init: E0923 13:25:57.718823       1 main.go:657] Failed to redirect output for CLI: creating log file: opening log file: open C:\Users\Denry\.gemini\antigravity-cli\log\cli-20260923_132557.log: Access is denied.
I0923 13:25:57.719434      40 server.go:1574] Starting language server process with pid 17340
E0923 13:25:57.719434      40 server.go:1550] Failed to initialize crash reporter: failed to setup crash output: open C:\Users\Denry\.gemini\antigravity-cli\crashes\crash_17340_1ac152cd-871e-4e32-bca3-bd9e4fb83cf7.log: Access is denied.
I0923 13:25:57.721173      40 server.go:1625] Language server version: 1.2.9
I0923 13:25:57.721173      40 server.go:610] Language server will attempt to listen on host localhost
I0923 13:25:57.732043      40 server.go:625] Language server listening on random port at 56592 for HTTPS (gRPC)
I0923 13:25:57.732607      40 server.go:633] Language server listening on random port at 56593 for HTTP
W0923 13:25:57.744015      76 crashreporter.go:122] No active crash reporter, cannot upload previous crashes
W0923 13:25:57.744015      75 cache.go:135] Cache(loadCodeAssistResponse): Singleflight refresh failed: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.744570      75 errorreport.go:224] error getting token source: You are not logged into Antigravity.
E0923 13:25:57.745670      75 errorreport.go:224] Failed to poll ListExperiments: error getting token source: You are not logged into Antigravity.
I0923 13:25:57.745670      75 model_configs.go:226] Auth mode is unspecified, skipping fetchAvailableModels and returning empty response
E0923 13:25:57.746794      40 summary_store.go:280] summary store open failed (corrupt_on_open), recreating: summary_store: open write db: unable to open database file: The system cannot find the file specified.
E0923 13:25:57.747328      40 summary_store.go:285] summary store recreate failed: summary_store: open write db: unable to open database file: The system cannot find the file specified.
W0923 13:25:57.750729      40 cache.go:135] Cache(loadCodeAssistResponse): Singleflight refresh failed: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.751272      40 errorreport.go:224] error getting token source: You are not logged into Antigravity.
W0923 13:25:57.751272      40 cache.go:135] Cache(userInfo): Singleflight refresh failed: failed to get load code assist response: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.751272      40 errorreport.go:224] failed to get load code assist response: error getting token source: You are not logged into Antigravity.
I0923 13:25:57.751272      26 store_client.go:697] summary store: starting background reconciliation (trigger=startup)
E0923 13:25:57.751828      26 summary_store.go:280] summary store open failed (corrupt_on_open), recreating: summary_store: open write db: unable to open database file: The system cannot find the file specified.
E0923 13:25:57.751828      26 summary_store.go:285] summary store recreate failed: summary_store: open write db: unable to open database file: The system cannot find the file specified.
E0923 13:25:57.751828      26 store_client.go:737] summary store: cannot reopen for reconciliation
W0923 13:25:57.751828      26 cache.go:135] Cache(loadCodeAssistResponse): Singleflight refresh failed: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.751828      26 errorreport.go:224] error getting token source: You are not logged into Antigravity.
W0923 13:25:57.751828      26 cache.go:135] Cache(userInfo): Singleflight refresh failed: failed to get load code assist response: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.751828      26 errorreport.go:224] failed to get load code assist response: error getting token source: You are not logged into Antigravity.
W0923 13:25:57.752846      40 cache.go:135] Cache(loadCodeAssistResponse): Singleflight refresh failed: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.752846      40 errorreport.go:224] error getting token source: You are not logged into Antigravity.
W0923 13:25:57.752846      40 cache.go:135] Cache(userInfo): Singleflight refresh failed: failed to get load code assist response: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.752846      40 errorreport.go:224] failed to get load code assist response: error getting token source: You are not logged into Antigravity.
W0923 13:25:57.752846      40 cache.go:135] Cache(loadCodeAssistResponse): Singleflight refresh failed: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.752846      40 errorreport.go:224] error getting token source: You are not logged into Antigravity.
W0923 13:25:57.753361      40 cache.go:135] Cache(userInfo): Singleflight refresh failed: failed to get load code assist response: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.753361      40 errorreport.go:224] failed to get load code assist response: error getting token source: You are not logged into Antigravity.
W0923 13:25:57.754377      40 defaults.go:702] failed to get cs path: cs path /usr/bin/cs invalid
I0923 13:25:57.754377      40 manager.go:108] Creating trajectory store manager with proto store and SQLite store
W0923 13:25:57.754377      40 cache.go:135] Cache(loadCodeAssistResponse): Singleflight refresh failed: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.754377      40 errorreport.go:224] error getting token source: You are not logged into Antigravity.
W0923 13:25:57.755401      40 cache.go:135] Cache(userInfo): Singleflight refresh failed: failed to get load code assist response: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.755401      40 errorreport.go:224] failed to get load code assist response: error getting token source: You are not logged into Antigravity.
I0923 13:25:57.755401     150 manager.go:88] Migration [MIGRATION_ID_SIDECAR_USER_CONFIG_BYPASS] is disabled, skipping entirely
I0923 13:25:57.755401     150 manager.go:91] Migration [MIGRATION_ID_SANITY_CHECK_PROJECT_URIS] is enabled
I0923 13:25:57.756400     150 manager.go:100] Migration [MIGRATION_ID_SANITY_CHECK_PROJECT_URIS] already has status MIGRATION_STATUS_COMPLETED, skipping
I0923 13:25:57.756400     150 manager.go:91] Migration [MIGRATION_ID_PLUGIN_ENABLEMENT] is enabled
I0923 13:25:57.756400     150 manager.go:100] Migration [MIGRATION_ID_PLUGIN_ENABLEMENT] already has status MIGRATION_STATUS_COMPLETED, skipping
I0923 13:25:57.756400     150 manager.go:91] Migration [MIGRATION_ID_BUILTIN_SIDECARS_TO_PLUGINS] is enabled
I0923 13:25:57.756400     150 manager.go:100] Migration [MIGRATION_ID_BUILTIN_SIDECARS_TO_PLUGINS] already has status MIGRATION_STATUS_COMPLETED, skipping
I0923 13:25:57.756400     150 manager.go:88] Migration [MIGRATION_ID_LIN_BUILTIN_TO_MARKETPLACE] is disabled, skipping entirely
I0923 13:25:57.756400     150 manager.go:88] Migration [MIGRATION_ID_ADOPT_BWG_INSTALLS] is disabled, skipping entirely
I0923 13:25:57.764477      40 server.go:3021] Auth succeeded, refreshing features and managers
W0923 13:25:57.764477      40 cache.go:135] Cache(loadCodeAssistResponse): Singleflight refresh failed: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.764477      40 errorreport.go:224] error getting token source: You are not logged into Antigravity.
E0923 13:25:57.765079      40 errorreport.go:224] Failed to poll ListExperiments: error getting token source: You are not logged into Antigravity.
I0923 13:25:57.765079      40 server.go:3028] State refresh took 0ms
I0923 13:25:57.765079      40 server.go:3039] [RemoteControl] Subscription callback triggered.
I0923 13:25:57.765673      40 server.go:3042] [RemoteControl] RemoteControlEnabled value: false
I0923 13:25:57.765673      40 server.go:3718] [RemoteControl] Session toggle is off, staying disconnected
I0923 13:25:57.765673      40 server.go:3429] [RemoteControl] Resolved proxyServerURL: ""
I0923 13:25:57.765673      40 profiler.go:231] Continuous pprof profiling is disabled.
I0923 13:25:57.765673     156 manager.go:88] Migration [MIGRATION_ID_SIDECAR_USER_CONFIG_BYPASS] is disabled, skipping entirely
I0923 13:25:57.765673     156 manager.go:91] Migration [MIGRATION_ID_SANITY_CHECK_PROJECT_URIS] is enabled
I0923 13:25:57.766216      40 server.go:2516] initialized server successfully in 46.7822ms
I0923 13:25:57.766216     156 manager.go:100] Migration [MIGRATION_ID_SANITY_CHECK_PROJECT_URIS] already has status MIGRATION_STATUS_COMPLETED, skipping
I0923 13:25:57.766216     156 manager.go:91] Migration [MIGRATION_ID_PLUGIN_ENABLEMENT] is enabled
W0923 13:25:57.766216     159 cache.go:135] Cache(loadCodeAssistResponse): Singleflight refresh failed: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.766216     159 errorreport.go:224] error getting token source: You are not logged into Antigravity.
I0923 13:25:57.766761     156 manager.go:100] Migration [MIGRATION_ID_PLUGIN_ENABLEMENT] already has status MIGRATION_STATUS_COMPLETED, skipping
I0923 13:25:57.766761     156 manager.go:91] Migration [MIGRATION_ID_BUILTIN_SIDECARS_TO_PLUGINS] is enabled
W0923 13:25:57.766761     159 cache.go:135] Cache(userInfo): Singleflight refresh failed: failed to get load code assist response: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.766761     159 errorreport.go:224] failed to get load code assist response: error getting token source: You are not logged into Antigravity.
I0923 13:25:57.766761     156 manager.go:100] Migration [MIGRATION_ID_BUILTIN_SIDECARS_TO_PLUGINS] already has status MIGRATION_STATUS_COMPLETED, skipping
I0923 13:25:57.766761     156 manager.go:88] Migration [MIGRATION_ID_LIN_BUILTIN_TO_MARKETPLACE] is disabled, skipping entirely
W0923 13:25:57.766761       1 auto_updater.go:274] Directory C:\Users\Denry\AppData\Local\agy\bin is not fully accessible (readable: true, writable: false), skipping update
I0923 13:25:57.766761     156 manager.go:88] Migration [MIGRATION_ID_ADOPT_BWG_INSTALLS] is disabled, skipping entirely
W0923 13:25:57.766761     163 cache.go:135] Cache(loadCodeAssistResponse): Singleflight refresh failed: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.766761     163 errorreport.go:224] error getting token source: You are not logged into Antigravity.
I0923 13:25:57.766761       1 common.go:151] Launching CLI mode
E0923 13:25:57.766761       1 launchsteps.go:84] Failed to resolve GeminiDir ".gemini": .gemini must be an absolute path: path is not absolute, falling back to default
W0923 13:25:57.766761     163 cache.go:135] Cache(userInfo): Singleflight refresh failed: failed to get load code assist response: error getting token source: You are not logged into Antigravity.
I0923 13:25:57.766761       1 common.go:173] CLI app data directory: C:\Users\Denry\.gemini\antigravity-cli
E0923 13:25:57.766761     163 errorreport.go:224] failed to get load code assist response: error getting token source: You are not logged into Antigravity.
I0923 13:25:57.766761       1 server.go:315] Creating CLI server backend: product=antigravity workspaceDirs=[C:\Users\Denry\Desktop\hack-a2928c88-hackai] appDataDir=C:\Users\Denry\.gemini\antigravity-cli cascadeManager=true codeAssist=true
I0923 13:25:57.767305       1 auth_provider.go:952] [AuthProvider] SetEnableBusinessLogin called with enable: true
W0923 13:25:57.767305     165 cache.go:135] Cache(loadCodeAssistResponse): Singleflight refresh failed: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.767305     165 errorreport.go:224] error getting token source: You are not logged into Antigravity.
W0923 13:25:57.767305     165 cache.go:135] Cache(userInfo): Singleflight refresh failed: failed to get load code assist response: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.767305     165 errorreport.go:224] failed to get load code assist response: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.767860       1 summary_store.go:280] summary store open failed (corrupt_on_open), recreating: summary_store: open write db: unable to open database file: The system cannot find the file specified.
E0923 13:25:57.767860       1 summary_store.go:285] summary store recreate failed: summary_store: open write db: unable to open database file: The system cannot find the file specified.
W0923 13:25:57.767860     179 cache.go:135] Cache(loadCodeAssistResponse): Singleflight refresh failed: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.768427     179 errorreport.go:224] error getting token source: You are not logged into Antigravity.
W0923 13:25:57.768427     179 cache.go:135] Cache(userInfo): Singleflight refresh failed: failed to get load code assist response: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.768427     179 errorreport.go:224] failed to get load code assist response: error getting token source: You are not logged into Antigravity.
I0923 13:25:57.768427       1 server.go:2211] Backend project ID updated dynamically to: default-cli-project
W0923 13:25:57.768427     179 cache.go:135] Cache(loadCodeAssistResponse): Singleflight refresh failed: error getting token source: You are not logged into Antigravity.
I0923 13:25:57.768427       1 analytics.go:187] CLI startup completed (took 116.8733ms)
E0923 13:25:57.768427     179 errorreport.go:224] error getting token source: You are not logged into Antigravity.
I0923 13:25:57.768427       1 printmode.go:181] Print mode: starting (promptLength=66, model="", conversationID="")
I0923 13:25:57.768427       1 manager.go:443] Initializing CLI store manager for workspace C:\Users\Denry\Desktop\hack-a2928c88-hackai
W0923 13:25:57.768427     179 cache.go:135] Cache(userInfo): Singleflight refresh failed: failed to get load code assist response: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.768985     179 errorreport.go:224] failed to get load code assist response: error getting token source: You are not logged into Antigravity.
W0923 13:25:57.768985     179 cache.go:135] Cache(loadCodeAssistResponse): Singleflight refresh failed: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.768985     179 errorreport.go:224] error getting token source: You are not logged into Antigravity.
W0923 13:25:57.768985     179 cache.go:135] Cache(userInfo): Singleflight refresh failed: failed to get load code assist response: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.768985     179 errorreport.go:224] failed to get load code assist response: error getting token source: You are not logged into Antigravity.
W0923 13:25:57.768985     179 cache.go:135] Cache(loadCodeAssistResponse): Singleflight refresh failed: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.768985     179 errorreport.go:224] error getting token source: You are not logged into Antigravity.
W0923 13:25:57.768985     179 cache.go:135] Cache(userInfo): Singleflight refresh failed: failed to get load code assist response: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.768985     179 errorreport.go:224] failed to get load code assist response: error getting token source: You are not logged into Antigravity.
I0923 13:25:57.770628       1 cli_setting_manager.go:156] applyUserSettings: no shared config permissions from C:\Users\Denry\.gemini\config\config.json
I0923 13:25:57.770628       1 cli_setting_manager.go:92] CLI settings initialized: permissions=&{Allow:[command(dotnet --version; dotnet --list-sdks) command(Get-Process | Where-Object { $_.ProcessName -match "yandex|music" }) command(Get-ChildItem -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall", "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall", "HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall" -ErrorAction SilentlyContinue | Get-ItemProperty | Where-Object { $_.DisplayName -match "Yandex|Яндекс|Music|Музыка" } | Select-Object DisplayName, DisplayVersion, InstallLocation, Publisher) command(Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*" | Where-Object { $_.DisplayName -match "5.109.1" -or $_.InstallLocation -match "YandexMusic" -or $_.UninstallString -match "YandexMusic" } | Format-List DisplayName, InstallLocation, UninstallString) command(New-Item -ItemType Directory -Force -Path "C:\Users\Denry\MusicIsland\Stage1_Research") command(dotnet new console -n MediaSessionProbe -o "C:\Users\Denry\MusicIsland\Stage1_Research\MediaSessionProbe") command(dotnet build "C:\Users\Denry\MusicIsland\Stage1_Research\MediaSessionProbe\MediaSessionProbe.csproj") command(dotnet run --project "C:\Users\Denry\MusicIsland\Stage1_Research\MediaSessionProbe\MediaSessionProbe.csproj" --no-build -- --dump) command(node -v; npm -v) command(npx --yes @electron/asar extract-file "C:\Users\Denry\AppData\Local\Programs\YandexMusic\resources\app.asar" package.json "C:\Users\Denry\MusicIsland\Stage1_Research\yandex_music_package.json")] Deny:[] Ask:[]}, toolPermission=always-proceed
I0923 13:25:57.770628       1 manager.go:1379] SetCycleMode called: accept-edits
W0923 13:25:57.771323     179 cache.go:135] Cache(loadCodeAssistResponse): Singleflight refresh failed: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.771323     179 errorreport.go:224] error getting token source: You are not logged into Antigravity.
W0923 13:25:57.771323     179 cache.go:135] Cache(userInfo): Singleflight refresh failed: failed to get load code assist response: error getting token source: You are not logged into Antigravity.
E0923 13:25:57.771323     179 errorreport.go:224] failed to get load code assist response: error getting token source: You are not logged into Antigravity.
I0923 13:25:57.772391       1 hooks_manager.go:53] loaded 0 named hooks from 0 hooks.json file(s)
I0923 13:25:57.772391       1 manager.go:627] CLI store manager initialized successfully
I0923 13:25:57.772391       1 printmode.go:372] Print mode: not authenticated, trying silent auth
I0923 13:25:57.772939       1 printmode.go:378] Print mode: silent auth failed
I0923 13:25:57.773476       1 printmode.go:395] Print mode: triggering interactive OAuth
I0923 13:25:57.773476       1 auth_manager.go:158] Starting OAuth authentication flow
I0923 13:25:57.773476       1 browser.go:56] consumerOAuth: starting OAuth flow
Authentication required. Please visit the URL to log in:
  https://accounts.google.com/o/oauth2/auth?access_type=offline&client_id=1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com&code_challenge=dH2zjIwNJmEznYNu81DMVXwK_gcx76SUrDUWKCVM3yw&code_challenge_method=S256&prompt=consent&redirect_uri=https%3A%2F%2Fantigravity.google%2Foauth-callback&response_type=code&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcloud-platform+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fuserinfo.email+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fuserinfo.profile+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcclog+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fexperimentsandconfigs+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Faicode+openid&state=RWpURDlWNYdMhPvo6zUHiw

Waiting for authentication (timeout 60s)...
Or, paste the authorization code here and press Enter:
E0923 13:26:02.754469      74 g3syslog.go:23] [Post "https://play.googleapis.com/log": dial tcp 172.217.118.4:443: connectex: An attempt was made to access a socket in a way forbidden by its access permissions.]
E0923 13:26:02.754999      71 client.go:68] Post "https://play.googleapis.com/log": dial tcp 172.217.118.4:443: connectex: An attempt was made to access a socket in a way forbidden by its access permissions.
E0923 13:26:07.768765      74 g3syslog.go:23] [Post "https://play.googleapis.com/log": dial tcp 172.217.118.4:443: connectex: An attempt was made to access a socket in a way forbidden by its access permissions.]
E0923 13:26:07.768765      71 client.go:68] Post "https://play.googleapis.com/log": dial tcp 172.217.118.4:443: connectex: An attempt was made to access a socket in a way forbidden by its access permissions.
E0923 13:26:12.779752      74 g3syslog.go:23] [Post "https://play.googleapis.com/log": dial tcp 172.217.118.4:443: connectex: An attempt was made to access a socket in a way forbidden by its access permissions.]
E0923 13:26:12.780900      71 client.go:68] Post "https://play.googleapis.com/log": dial tcp 172.217.118.4:443: connectex: An attempt was made to access a socket in a way forbidden by its access permissions.
E0923 13:26:17.786553      74 g3syslog.go:23] [Post "https://play.googleapis.com/log": dial tcp 172.217.118.4:443: connectex: An attempt was made to access a socket in a way forbidden by its access permissions.]
E0923 13:26:17.787683      71 client.go:68] Post "https://play.googleapis.com/log": dial tcp 172.217.118.4:443: connectex: An attempt was made to access a socket in a way forbidden by its access permissions.
E0923 13:26:22.810424      71 client.go:68] Post "https://play.googleapis.com/log": dial tcp 172.217.118.4:443: connectex: An attempt was made to access a socket in a way forbidden by its access permissions.
E0923 13:26:22.811584      74 g3syslog.go:23] [Post "https://play.googleapis.com/log": dial tcp 172.217.118.4:443: connectex: An attempt was made to access a socket in a way forbidden by its access permissions.]
E0923 13:26:27.877517      71 client.go:68] Post "https://play.googleapis.com/log": dial tcp 172.217.112.4:443: connectex: An attempt was made to access a socket in a way forbidden by its access permissions.
E0923 13:26:27.877517      74 g3syslog.go:23] [Post "https://play.googleapis.com/log": dial tcp 172.217.112.4:443: connectex: An attempt was made to access a socket in a way forbidden by its access permissions.]
E0923 13:26:32.888269      74 g3syslog.go:23] [Post "https://play.googleapis.com/log": dial tcp 172.217.112.4:443: connectex: An attempt was made to access a socket in a way forbidden by its access permissions.]
E0923 13:26:32.889271      71 client.go:68] Post "https://play.googleapis.com/log": dial tcp 172.217.112.4:443: connectex: An attempt was made to access a socket in a way forbidden by its access permissions.
E0923 13:26:37.898344      74 g3syslog.go:23] [Post "https://play.googleapis.com/log": dial tcp 172.217.112.4:443: connectex: An attempt was made to access a socket in a way forbidden by its access permissions.]
E0923 13:26:37.898901      71 client.go:68] Post "https://play.googleapis.com/log": dial tcp 172.217.112.4:443: connectex: An attempt was made to access a socket in a way forbidden by its access permissions.
E0923 13:26:42.917877      74 g3syslog.go:23] [Post "https://play.googleapis.com/log": dial tcp 172.217.112.4:443: connectex: An attempt was made to access a socket in a way forbidden by its access permissions.]
E0923 13:26:42.917877      71 client.go:68] Post "https://play.googleapis.com/log": dial tcp 172.217.112.4:443: connectex: An attempt was made to access a socket in a way forbidden by its access permissions.
E0923 13:26:47.937578      71 client.go:68] Post "https://play.googleapis.com/log": dial tcp 172.217.112.4:443: connectex: An attempt was made to access a socket in a way forbidden by its access permissions.
E0923 13:26:47.938769      74 g3syslog.go:23] [Post "https://play.googleapis.com/log": dial tcp 172.217.112.4:443: connectex: An attempt was made to access a socket in a way forbidden by its access permissions.]
E0923 13:26:52.951414      71 client.go:68] Post "https://play.googleapis.com/log": dial tcp 172.217.112.4:443: connectex: An attempt was made to access a socket in a way forbidden by its access permissions.
E0923 13:26:52.951953      74 g3syslog.go:23] [Post "https://play.googleapis.com/log": dial tcp 172.217.112.4:443: connectex: An attempt was made to access a socket in a way forbidden by its access permissions.]
W0923 13:26:57.744153      75 cache.go:135] Cache(loadCodeAssistResponse): Singleflight refresh failed: error getting token source: You are not logged into Antigravity.
E0923 13:26:57.744676      75 errorreport.go:224] error getting token source: You are not logged into Antigravity.
E0923 13:26:57.745222      75 errorreport.go:224] Failed to poll ListExperiments: error getting token source: You are not logged into Antigravity.
E0923 13:26:57.773861       1 printmode.go:445] Print mode: auth timed out
Error: authentication timed out.
error: authentication failed or timed out
I0923 13:26:57.773861       1 manager.go:807] CLI store manager shutting down
I0923 13:26:57.774558     331 server.go:2880] Language server shutting down
I0923 13:26:57.774558     331 server.go:2885] Waiting for migrations to complete to prevent partial migration state...
E0923 13:26:57.775715     118 file_watcher.go:194] skipping empty or temp file: 
E0923 13:26:57.788885     331 server.go:2975] Failed to shutdown telemetry client: Post "https://play.googleapis.com/log": dial tcp 172.217.112.4:443: connectex: An attempt was made to access a socket in a way forbidden by its access permissions.
