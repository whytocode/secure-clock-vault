#!/usr/bin/env python3
"""Build an allowlisted static site from verified, locally held release assets."""

import argparse
import hashlib
import html
import json
import re
import shutil
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
ASSETS = ("icon.svg", "site.css", "site.js", "library.png", "review.png", "members.png")
LICENSES = ("Native-dependencies.txt", "SimpleX-AGPL-3.0.txt",
            "SimpleX-Conditions.txt", "ZXing-Apache-2.0.txt")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repository_name(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,38}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", value):
        raise argparse.ArgumentTypeError("Use an approved GitHub owner/repository, not a URL.")
    return value


def verify_artifacts(directory, release):
    for prefix in ("apk", "source"):
        filename = release[f"{prefix}Filename"]
        if Path(filename).name != filename or "\\" in filename:
            raise ValueError("Release filenames must not contain paths.")
        asset = directory / filename
        if asset.stat().st_size != release[f"{prefix}Bytes"]:
            raise ValueError(f"Size mismatch: {filename}")
        if sha256(asset) != release[f"{prefix}Sha256"]:
            raise ValueError(f"SHA-256 mismatch: {filename}")
    with ZipFile(directory / release["sourceFilename"]) as archive:
        for name in ("LICENSE", "NOTICE", "app/build.gradle.kts"):
            if archive.read(f"SecureClockVault/{name}") != (REPO / name).read_bytes():
                raise ValueError(f"Source archive does not match current {name}")


def render(template, values):
    missing = set(re.findall(r"\{\{([A-Z_0-9]+)\}\}", template)) - values.keys()
    if missing:
        raise ValueError(f"Missing template values: {sorted(missing)}")
    return re.sub(r"\{\{([A-Z_0-9]+)\}\}", lambda match: values[match[1]], template)


def build(directory, output, repository=None):
    release = json.loads((ROOT / "release.json").read_text())
    verify_artifacts(directory, release)
    output = output.resolve()
    if not output.is_relative_to((REPO / "build").resolve()) or output == (REPO / "build").resolve():
        raise ValueError("Output must be a named subdirectory of this repository's build directory.")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Output is not empty. Choose a new build directory; no files were removed.")

    values = {
        "STYLESHEET_URL": f'assets/site.css?v={sha256(ROOT / "assets/site.css")[:12]}',
        "SCRIPT_URL": f'assets/site.js?v={sha256(ROOT / "assets/site.js")[:12]}',
        "VERSION": html.escape(release["version"]),
        "APK_SIZE": f'{release["apkBytes"] / 1_000_000:.1f} MB',
        "APK_SHA256": release["apkSha256"],
        "SOURCE_FILENAME": html.escape(release["sourceFilename"]),
        "SOURCE_SIZE": f'{release["sourceBytes"] / 1_000_000:.1f} MB',
        "SOURCE_SHA256": release["sourceSha256"],
        "CERT_SHA256": release["certificateSha256"],
    }
    if repository:
        repository = repository_name(repository)
        base = f"https://github.com/{repository}"
        # Pin the release tag: old cached pages must not point at a different APK
        # after an update. The asset filename itself stays stable.
        downloads = f'{base}/releases/download/v{release["version"]}'
        apk_url = f'{downloads}/{release["apkFilename"]}'
        source_url = f'{downloads}/{release["sourceFilename"]}'
        values.update(
            DOWNLOAD_ACTIONS=f'<div class="download-actions"><a class="button primary" href="{apk_url}">Download APK <span aria-hidden="true">&darr;</span></a><a class="text-link" href="{source_url}">Matching source &amp; build materials</a></div>',
            PUBLICATION_STATUS="Downloads are served by GitHub. No sign-in is required.",
            SOURCE_LINK=f'<a href="{source_url}">Download the corresponding source archive.</a>',
            SUPPORT_LINK=f'<a href="{base}/issues">Public issue tracker</a>',
            SUPPORT_DESCRIPTION="The public GitHub issue tracker accepts non-sensitive bug reports and source-availability requests. Reports and replies are publicly visible.",
        )
        release["repository"] = repository
        release["apkUrl"] = apk_url
        release["sourceUrl"] = source_url
        release["siteUrl"] = f'https://{repository.split("/")[0].lower()}.github.io/{repository.split("/")[1]}/'
    else:
        values.update(
            DOWNLOAD_ACTIONS='<div class="download-actions"><span class="preview-label">Preview &mdash; public downloads are not live</span></div>',
            PUBLICATION_STATUS="Publication is awaiting approval of the owning GitHub account. There is no public download URL yet.",
            SOURCE_LINK="The verified source archive is prepared locally; no public download has been published yet.",
            SUPPORT_LINK="A public issue tracker has not been configured.",
            SUPPORT_DESCRIPTION="Public support has not been configured for this unpublished preview.",
        )
        release["repository"] = None

    output.mkdir(parents=True, exist_ok=True)
    for page in ("index.html", "privacy.html"):
        (output / page).write_text(render((ROOT / page).read_text(), values))
    (output / "assets").mkdir()
    for filename in ASSETS:
        shutil.copyfile(ROOT / "assets" / filename, output / "assets" / filename)
    (output / "licenses").mkdir()
    for name in ("LICENSE", "NOTICE"):
        shutil.copyfile(REPO / name, output / "licenses" / f"{name}.txt")
    for name in LICENSES:
        shutil.copyfile(REPO / "app/src/main/assets/licenses" / name, output / "licenses" / name)
    (output / ".nojekyll").touch()
    (output / "release.json").write_text(json.dumps(release, indent=2) + "\n")
    if not repository:
        (output / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
    print(f"Built {'public configuration' if repository else 'unpublished preview'}: {output}")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--repository", type=repository_name,
                        help="Only set after the user approves the public GitHub owner/repository.")
    args = parser.parse_args()
    build(args.artifacts.resolve(), args.output, args.repository)


if __name__ == "__main__":
    main()
