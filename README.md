# Secure Clock Vault

An independent Android encrypted file vault and clock application.
This repository contains the public website, its original source, and release notices.
The website brings together 20 searchable feature cards, screenshots, clock artwork,
sharing comparisons, six how-to guides, security information, downloads, and FAQs.

- [Website and installation help](https://whytocode.github.io/secure-clock-vault/)
- [Current release](https://github.com/whytocode/secure-clock-vault/releases/latest)
- [Privacy, security limits, and licensing](https://whytocode.github.io/secure-clock-vault/privacy.html)

## Download and update

Release 3.20 supports Android 8.0+ on ARM64 and ARMv7 devices.
Download **SecureClockVault-release.apk** from Releases. Install updates over the
existing app; **do not uninstall or clear app data** to update. Keep a separately
created, verified library backup.

The APK uses the existing release signing identity. The website's release panel
provides its SHA-256 checksum. A checksum or signature is not an independent
security certification.

## Corresponding application source

Every APK release includes the specifically named
**SecureClockVault-3.20-source.zip** attachment, at no extra charge. It contains the
matching application source, build configuration, native build recipes, and all
11 pinned upstream source archives.

GitHub's automatically generated **Source code (zip)** or **Source code (tar.gz)**
for this website repository is **not** the Android application's corresponding
source. Download the explicitly named application-source attachment instead.

Release signing private keys, signing passwords, and user vault data are not
included. Rebuilding the app uses the builder's own signing identity.

## Website source and rebuilding

The original, unminified website templates, styles, JavaScript, images, build
scripts, and tests are in [`website-source/`](website-source/).
The rendered website is at the repository root.

To recreate the builder's directory layout, extract the matching application-source
archive, copy `website-source/` to `SecureClockVault/website/`, and follow
[`website-source/PUBLISHING.md`](website-source/PUBLISHING.md).
The builder requires Python 3.9+ and the verified release APK/source files. It
does not need npm, external fonts, analytics, or a backend.

The screenshots use synthetic demo files. The clock tile and analog dial are original
illustrative website artwork, not application screenshots. Feature search runs locally
in the browser; the complete catalogue and guides also work without JavaScript.

## Licensing and support

The application and website are distributed under **AGPL-3.0-only**, without
warranty to the extent permitted by law. See [LICENSE](LICENSE), [NOTICE](NOTICE),
and the individual [third-party notices](licenses/).
The app is not affiliated with or endorsed by SimpleX Chat Ltd.

The issue tracker is public and accepts non-sensitive bug reports and
source-availability requests. Do not post passwords, private files, messages, or
other people's personal information. There is no password-recovery service.
