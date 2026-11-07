# Public NXTPAPER beta — 5 November 2026

Status: IMPLEMENTATION IN PROGRESS. No beta build or physical acceptance yet.

Latest user steering (7 November 2026): **The phone is NOW connected; testing is authorized NOW.** This supersedes the earlier phone-later request. Explicit-serial read-only inspection found AMD9, installed1.0.5/code6 debug, Shizuku running and an exact-known 1.0.5 controller at WAIT_SWITCH with no active commitment reported. Preserve the installation/data. Test a matching development-signed update after source verification and a safe supported controller stop; do not replace a live/unknown controller. Exact permanent-key release acceptance needs a separately chosen signing migration; no uninstall/data clear is authorized. No publication before acceptance gates.

## Authorization and objective

The founder explicitly requested implementation of the public beta plan: experimental guided compatibility setup for eligible unfamiliar TCL NXTPAPER slider phones/builds, existing native commitment rules preserved, firmware-change requalification, redacted user-controlled reports, Apache-2.0, new permanent release key, version1.0.6-beta.1/code7, GitHub prerelease and ShizuCoreFetch distribution. Izzy eligibility is deferred due its current AI-code policy; no acceptance claim. Preserve stock firmware/personal data and existing installation/controller; no automatic uninstall, controller replacement, updater restriction, root/reset/flashing. Public release is gated on local checks and coordinated physical acceptance.

## Starting state and existing work

Repository C:\AnalogAnchor_NXTPAPER_Demo, codex/nxtpaper-demo, HEAD307a633. Existing modifications: HANDOFF/LATEST.md and untracked HANDOFF/history/2026-11-04_172700_website-link-and-arazi-hash-setup.md. Preserve these; LATEST archived before new checkpoint. GitHub repository already public under arazi-hash; handoff's create-repo instruction is stale. Latest known source/APK1.0.5/code6 remains single AMD9 profile, debug-signed. Historical tests217 Python+25 Android, not current-task proof.

## Required behavior

- Registry and reviewed slider adapter separate device identity from native protocol. Exact AMD9 pin retained as historical mapping. Unknown candidates require vendor.software.support.tcl_switch, actual active layout, valid native fields/configuration, raw events and runtime symbolic key resolution; no numeric fallback to343/344 on unknown builds. Push/cycle interaction remains unsupported.
- Visible normal setup flow, passive physical Normal→Ink→Normal proof followed by supervised bounded software exit/re-entry/restoration; 45-second transitions, independent shell lifetime, immediate trial abort, no commitment/Stop cooldown. Success requires actual Normal restoration plus owner acknowledgement of native launcher/restrictions. No active/unknown guard replacement.
- Local qualification bound to build, adapter/controller digest, active layout hash/mapping and native package versions, excluding boot-dependent event node number. Fresh command checks remain authoritative. Reboot does not recover old commitments.
- Public signed release APK, validated Shizu metadata/category/download URL, tracked EN/AR publication assets, source license/notices/privacy, updated README/compatibility list/Gemini handoff. Release APK only + checksum/notes, never private recovery kit/debug APKs/keys.

## Work allocation and verification

Root owns orchestration, build/signing configuration/key creation, publication metadata/docs, checkpoints and integration/phone coordination. Agents will own shell trial/controller, Android setup/runtime/UI, and shared registry/PC helpers/tests separately. Agree contracts before overlapping consumers change. Run meaningful focused tests and then integrated suite/build after stable source. Do not claim publication or handset acceptance from mocks/artifact checks. No operation running at this initial checkpoint.


## 7 November progress

- Phone testing now authorized. Read-only backup saved privately under ignored logs/public-beta-device-2026-11-07: installed1.0.5 APK, app preferences, exact old controller/profile. Firmware AMD9; Shizuku13.6 running. Initial native TSWT_state=-1 with settled normal styles, preset3/immediate1.
- Exact-known old controller hash ce53dfb10c91beddabfbd8c4101db690ff9bfe8ab1ddb939b59378ca11721834 was WAIT_SWITCH/no active commitment. Supported request-stop returned STOPPED; no forced kill, native command, app installation or data reset.
- Public signing key created privately previously; verified local private backup only. Public certificate SHA256434a6ec4f84e1720f8f05e826fe2ccc0d148c47df73e561eac02d1b6f0845202 committed as public certificate files under release/. Second-PC private backup pending.
- Shizu metadata passes cached upstream draft7 schema (SHA256dd27553e3f65257e717da5e1505377994827e56a901ecb5c1031f3226579703f) with jsonschema4.26.0. Fresh screenshots not yet present. Root publication verifier validates metadata and optionally signed APK/assets.
- README/license/privacy/Fastlane metadata/release docs prepared. Shell, Android and PC implementation remain in progress; no beta build or beta physical acceptance yet.


## Final local verification in progress (7 November)

All three implementation owners finished first source pass. Read-only actual phone report now recognizes AMD9/tcl-slider-v1 and reports setup REQUIRED; no new mode commands sent. Full Python unittest discovery and Gradle testDebugUnitTest/lintDebug/lintRelease/assembleDebug/assembleRelease are running; logs under ignored logs/public-beta-*-2026-11-07.txt. Initial Android test/lint pass had32tests,0failures,0linterrors/17warnings; source changed afterwards so this is not final proof. Recovery review found deployment mutex needsbootowner and potential staleguardlockrebootrecovery; owners reviewing before install. Public release held pending exactsigneracceptance.


## First beta installation / actual device discovery

Matching-debug1.0.6-beta.1/code7 installed in place withadbinstall-r; succeeded, appdata preserved, no uninstall. DebugAPK SHA2568f8e26a6eb52f65f513d7c3236281f11f87cadb0c7a0abf248f2876e0df38e7b at this first pass. Controller remainedSTOPPED; no newtrial/nativecommand/qualification. ActualKeySymbolProbe found exactAMD9quirk: keyCodeFromStringTSWT343/344 butreverse namesKEYCODE_FP_LIFT_UP/KEYCODE_FP_LONGPRESS. Initialappcorrectlylockedsetup; Android/PCaddingpreciseexactAMD9aliasexception only, unknownbuildsamepairremainsunsupported. Need rebuild/reinstallafterfix.

SecondPythonrun268cases had4failures because it loadedfixturebeforeconcurrenttimeoutshimeditwhileexecutingscriptupdatedlater; agentsconfirmtargetedcurrentsnapshotpasses, fullfreezeverificationstillpending. Do notcountthatpass. Finaltest/lintbuild2m37passedbeforealiasfix; assets/signingverified release5064603bytesSHA256f0a56d3a8b8844833c006ca2b1039a3074995063e6ef506495eda5a470e05e32 but willchangeafterfix. Androidtimeoututilitysanity returned124 fortimeout1sleep5.


## Frozen checks and coordinated first physical attempt

Final frozenfullPython271passed161.220s; Android33passed; testDebugUnitTest/lintDebug/lintRelease/assembleDebug/assembleRelease passed1m28. Bothlint0errors/18warnings. SignedreleaseAPK5065231bytesSHA256862c3d9151388895cbfe9ad0814d070442f227e5c420dd8263e10673e3a4ae8e, correctpermanentcert/nondebuggable/notestOnly andallbundleassetsbyteequal; stagedunderignored dist/public-beta-1.0.6-beta.1. DebugAPK809cfb3df4fbe621e307166a375be64f601aabdc7bc1f5f02e03b3bd9dd2b53e installed-r; actualEN/AReligibilityshowsreviewedadapter/setupREQUIRED; Startdisableduntilpass. Ownerreadyconfirmed.

Firstattempt: openedrecoveryconsent andtappedStart; ownermovedphysicalInk beforePCconfirmedmonitor. NativeMaxInkappeared butNOnewcontroller/setupfilesweredeployed, old1.0.5guardremainedSTOPPED. Noqualification/commitment. IdentifiedrealUIrace: runSetup silentlyreturns ifpassiveSTATUSpollinflight whileownerconsentpositiveclicked. Androidownerfixingqueuedexplicitactions/cancelpriority; mustrebuild/reinstall/recheckbeforephysicalretry. UseraskedreturnNormal andwait. Do notcountunmonitoredmovementasguidedproof. PrivateUIcaptureincludesnativeappnames; neverpublishit. OnlypreflightEN/ARappcapturecandidatesarenonpersonal.


## Phone-start fixes in progress

Ownerconfirmedholderremoved,phoneNormal/physicalNormal,testingstillauthorized. AndroidagenthitusagecapafterwritingSetupCommandQueue.kt,4testsandMainActivityintegration; rootinspectedpartialworkandisbuildingtest/lint/debug/release now(log public-beta-phone-fixes-build-2026-11-07.txt). Oldpassivewatchercouldnotobservestartbecause noprocesswasdeployed. Rootread-onlynewsourceinAndroidshellcaughtawkprintfternarysyntaxerror PROFILE_INVALID; parenthesizedexpressionfixed. Actualreadonlyschema2shellpreflightnowVERIFIED:t807d-eea-amd9,stderrEMPTY, no modecommands. Targetedcompat/setupregressionsrunning(log public-beta-phone-fixes-shell-2026-11-07.txt). NeednewAPKinstallandverifyWAIT_NORMALbeforeaskingownerphysicalmovements. Previousartifactsareobsoleteafterparser/queuefixes. Rootownsallfilesnow; donotassumefailedagentfinishedverification.


## Actual guided setup PASSED on phone

Finalqueue/Androidawkfix build passed5m30;37Androidtests,0failures;50focusedcontroller/setupregressionspassed156.091s; finalfullPython271passed307.391s. PrivateacceptanceAPK isNONDEBUGGABLEreleasewithhistoricalmatchingcert; everyAPKZIPentryexceptsigningmetadata isbyteequal topublicpermanent-keyrelease. PublicSHA2560f75150dcc5d930739d65091551da2decf0e78547a653f517375c49b10675ee9; privateacceptanceSHA2562da0f47a4b76a3300da1b0daaa6943bc13a859c29c6571c7c92f03f3909f0cdc. Installed-rpreserveddata; pkgFlags noDEBUGGABLE. Thisdoesnotclaimpubliccertinstalled; founderpublickeymigrationstillseparate.

Secondcoordinatedguidedtrialpassed: initializedgenuinephysicalOFF, observedfullNormal→Ink→Normal, ownerconfirmedfullnativeMaxInk/restrictions, softwareexitwithphysicalONpassed, ownerphysicalOFFthenautomaticentry→restorationpassed, ownerfinalNormalconfirmationrecorded. ActualtrialQUALIFIEDelapsed309s, nativeTSWT/Ink/Book/Applying/Animationall0, appUIsetupcompleteandStartenabled. Firsttrialhadpassedphysicalpartbuttimedoutwhilecoordinatorwaited; stayedincomplete,Normalpreserved; noqualificationbypass. Actualactivityclosed/reopenedthroughnativeInkandprogresssurvived. PHYSICAL_TIMEOUT120 andINITIALIZINGstatusvisibility couldbenefitfromlaterUXrefinement; sourcecurrentlyunchanged tofinishacceptance. ENqualifiedscreenshotprivate captured. BeganappStart5mindefault; checkactualguardreadinessbeforeownerInk.


## Actual commitment acceptance passed / final UX follow-up

Default5m session: exactstart143169 deadline143469; genuinephysicalNormal exitrecoverednativeInk~16swithdeadlineunchanged; ownerconfirmedrecovery. RepeatedStoprequests keptsameexitdeadline; Continuecancelledexitwithoutchangingoriginaldeadline. NaturalexpirybecameEXTENDEDwithphysicalON,ownerthenphysicalOFFreturnedNormalandstayed; no timerrenewal. Real2hpreset selectedinapp, sessionstart143672 deadline150872; nextdurationreset300. RealStop/repeat/Continue/re-request throughcontrollerprotocol: finalexitdeadline144028=143728+300. Sleep10s preservedbothdeadlinesandcountdownadvanced. Actualrestorationbegan144029andNormalfullysettled144038, controllerSTOPPED, physicalONuntilownerfinalNormalconfirmationpending. TheseStop/Continuecommandsusedcontrollerprotocol,noton-screenbuttonswhileapprestrictedbyMaxInk. No unknown/liveoriginalcontrollerwasreplaced; thesewereoursignedcopytestcommitments. Logs default-session-watch/full-stop-watch JSONL, default-stop-continue.json, full-stop-timing.json, sleep-during-exit-wait.json privateunderlogs/public-beta-device-2026-11-07.

FinalUXfollow-up inprogress: actualstartupinitiallyreportedtransientFAILEDwhilepreflighthadnotyetpublishedPID/state. Newsetup_mainpublishes INITIALIZINGidentityfirstandWAIT_NORMALonlyaftermonitorready; realstatequalgatesunchanged. EN/ARpreparing/physicalinitializationinstructionsmadeplain; passivepollingnolongerdisablesownerbuttons(queuedowneractionsalreadytested). Rootbuilding/testlintreleasein logs/public-beta-final-ux-build-2026-11-07.txt and20setupregressionsinlogs/public-beta-startup-regressions-2026-11-07.txt. No furthercorechangesplanned. LivecontrolleralreadySTOPPED;ownerphysicalNormalconfirmationpending; reinstallfinalnondebuggableprivateacceptancecopysignature-onlyequaltofinalpublicAPK,retainqualificationifbindingunchanged. Needfinalassetinspection/screenshots/metadata/docs/signingbackupdestination/GitHubpublicationgates. PublicAPKstagingcurrentlyobsoletebecausefinalUXbuildwillchangehash; neverpublishprivateacceptancecopy.


## Latest user steering: startup compatibility popup (7 November)

FounderattachedlargecompatibilitycardandrequestedstartupPOPUP/expandcollapsetoreducescrolling. RootpromisedcompactexpandablePhoneSetuprow; startupguideonlywhensetuprequired; dismiss=>remindnextentry, explicitreadackboundcurrentdevicebinding; relevantchangebringsreminderback; nopopupoveractivetrial/livecommitment; dismissalneverqualifies. Agentsetup_popup_uxownsonlyMainActivity/layout/ENARstrings/popup-policytests; agentrelease_evidence_docsownsREADME/FINDINGS/docsCOMPATIBILITY/RELEASENOTES; final_beta_safety_auditreadonlyreviewscoreshell/PC/GuardRuntime. Rootownsothers. DoNOTpublisholdAPK/assets; newpopupbuild/phoneUIvalidationrequired.

Desktopprivatebackupcreatedandhashverifiedat C:/Users/DELL/Desktop/Analog Anchor - PRIVATE Release Key Backup, withencryptedP12, privatepasswordtemplate, homePCinstaller(.cmd/.ps1),READ_ME_FIRSTandpubliccert. Installerparsedsyntaxonly; notrunonhomePC. OwnerwilltransferUSB/privateDrive; nocloudprivateuploadperformed. No secretvaluesinrepoorchat.

GitHubbrowserloginasARAZI-HASHconfirmedthroughownerpage. OfficialGCMdeviceflowcompletedusingexistingauthorizedapppermissions; correctaccountCLI/APIpushpermissionverifiedtrue (keepotheraccountanchorminimalism-del unchanged; usegit-c credential.username=arazi-hash). RepoAboutdescriptionupdatedthroughbrowsertoexperimentalcompatibilitylimitsandwebsite, removedeye-strainclaim. NOsourcecommit/push/tag/releaseyet. ExistingremoteHEADstill307a633,notags. BrowserIABtab2currentdeviceactivationSUCCESS,tab1GitHubhome; CUAauthcompletionreported. CanpublishviaGit/APIoncefilesreviewed/finaltests/assetscomplete,existinguserauthorizationimplementsfullplan.

Finalprepopupsourcechecks272Pythonpassed315.643s;37Androidpassed,releasebuild2m4; finalpublicAPKbeforepopupUI SHA256e968f5b341d24c60564bd98c556ce97b33b62dee8f30e5f1440d7342acd18e91; privatecopy58520775127e62e72f79e5c82555efbf1546835d785ccfbb0a3c980cf88eaf64 installed-r, everyentryexcludingsigningmetadataequal. ThisAPKwillbeobsoleteafterpopupUIbuild. PhoneNormalandcontrollerSTOPPEDdesiredfalse; localechangingforENARscreenshots, restoreEnglishwhenfinished. UserconfirmedfinalNormalafterreal300sStop. CurrentupstreamShizuschemaNov7hashunchangeddd275...validated. CommitrealENARscreenshotsafternewpopupUIprivacyreview.


## Final UI and release readiness

The compact startup guide passed actual English and Arabic UI checks on the final non-debuggable private acceptance copy. Later showed the guide on the next foreground visit, Got it suppressed it for the same binding, language recreation did not duplicate it, and manual guide opening and Show/Hide worked. Start stayed disabled while setup was incomplete. The test temporarily hid only app-local qualification preferences, restored their original bytes, verified the central qualification record was byte-identical, and returned the phone to Normal with its controller stopped. The earlier physical session evidence uses the same shipped commitment-controller bytes. Startup Cancel retention and uncertain native-command restoration have targeted host tests.

Final frozen source: 276 Python tests in 321.433 seconds, 43 Android tests, zero release lint errors and 19 warnings, successful debug/release builds. Public APK 5,079,619 bytes, SHA256 ab92945d1728891060d7a753f2d7ac448ca0ead5313cf3dd4540f2d5e792c4ac. Exact APK entry equality except signing metadata verified against private acceptance copy SHA256 96db44920c2386930a990bc521a8e3011f2e356f25340e16292d044dd7c76dbb. Four real Fastlane publication captures (EN/AR main and guide) cropped to remove the notification bar. Shizu metadata and artifact checks passed. No supported model beyond AMD9 claimed.

Next: commit reviewed public files, fast-forward the existing branch, publish the genuine prerelease with the final APK/checksum/notes, verify tagged source and real downloads, check actual ShizuCoreFetch catalog listing, and record the final URLs. Keep untracked historical checkpoints private. No release yet at this checkpoint.


## Publication result — 7 November 2026

Published genuine GitHub prerelease [v1.0.6-beta.1](https://github.com/arazi-hash/AnalogAnchor_NXTPAPER_E-Ink-Pre-Commitment-Mode/releases/tag/v1.0.6-beta.1) in the existing arazi-hash repository. The tag resolves to `a7b5f5cff8451207186cf4bc622238b7dd8b2112` on the default branch. All three public assets downloaded anonymously and matched the local signed APK, checksum and release notes. Tagged `shizu_store.json`, icon, banner, and four EN/AR images matched source bytes. Only public release material was attached. The repository description and topics reflect the experimental Shizuku/NXTPAPER scope.

ShizuCoreFetch discovery is CONFIRMED LIVE on 7 November 2026. Live catalog returned entry `arazi-hash/analoganchor_nxtpaper_e-ink-pre-commitment-mode`, matching package `com.analoganchor.nxtpaperguard`, version `v1.0.6-beta.1`, APK download URL, and exact size 5,079,619 bytes (`hasJsonStore: true`, `data_source: "shizu_store"`). The existing GitHub prerelease is available independently. IzzyOnDroid was not submitted.

The phone is in Normal with the controller stopped and prior local setup restored. The founder's installed private release test copy uses the historical signer. The public permanent signing key backup is ready for private transfer from the work PC Desktop. No home-PC transfer was verified.
