import importlib.util
import json
import os
import tempfile
import unittest
from argparse import ArgumentTypeError
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("site_build", ROOT / "scripts/build.py")
site_build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(site_build)


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.ids, self.links, self.images, self.elements = [], [], [], []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.elements.append((tag, attrs))
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag in ("a", "link", "script", "img"):
            value = attrs.get("href", attrs.get("src"))
            if value:
                self.links.append((tag, value))
        if tag == "img":
            self.images.append(attrs)


class SiteTests(unittest.TestCase):
    def test_templates_are_complete(self):
        self.assertEqual(site_build.render("{{VERSION}} {{VERSION}}", {"VERSION": "3.20"}), "3.20 3.20")
        with self.assertRaises(ValueError):
            site_build.render("{{MISSING}}", {})

    def test_repository_validation(self):
        self.assertEqual(site_build.repository_name("example/secure-clock-vault"), "example/secure-clock-vault")
        for invalid in ("https://github.com/a/b", "../other", 'a/b" onclick="x', "a/b/c", "a/..", ""):
            with self.subTest(invalid=invalid), self.assertRaises(ArgumentTypeError):
                site_build.repository_name(invalid)

    def test_document_structure(self):
        for filename in ("index.html", "privacy.html"):
            document = Document((ROOT / filename).read_text())
            with self.subTest(filename=filename):
                self.assertEqual(len(document.ids), len(set(document.ids)))
                self.assertEqual(sum(tag == "h1" for tag, _ in document.elements), 1)
                self.assertTrue(all("alt" in img and "width" in img and "height" in img for img in document.images))
                self.assertFalse(any(tag == "form" for tag, _ in document.elements))
                self.assertTrue(any(tag == "html" and attrs.get("lang") == "en" for tag, attrs in document.elements))
                policies = [attrs["content"] for tag, attrs in document.elements
                            if tag == "meta" and attrs.get("http-equiv") == "Content-Security-Policy"]
                self.assertEqual(len(policies), 1)
                self.assertIn("connect-src 'none'", policies[0])
                for tag, link in document.links:
                    if tag != "a":
                        self.assertFalse(urlsplit(link).scheme, "No third-party runtime assets")

    def test_release_metadata(self):
        release = json.loads((ROOT / "release.json").read_text())
        self.assertEqual(release["apkFilename"], "SecureClockVault-release.apk")
        self.assertEqual(release["sourceFilename"], f'SecureClockVault-{release["version"]}-source.zip')
        for key in ("apkSha256", "sourceSha256", "certificateSha256"):
            self.assertRegex(release[key], r"^[0-9a-f]{64}$")

    def test_feature_catalogue_contract(self):
        document = Document((ROOT / "index.html").read_text())
        elements = {attrs["id"]: (tag, attrs) for tag, attrs in document.elements if "id" in attrs}
        cards = [attrs for tag, attrs in document.elements if "data-feature-card" in attrs]
        filters = [attrs for tag, attrs in document.elements if "data-category" in attrs]
        categories = {attrs["data-category"] for attrs in filters} - {"all"}
        self.assertEqual(len(cards), 20)
        self.assertEqual(categories, {"library", "media", "clock", "sharing", "tools"})
        self.assertEqual([attrs["data-category"] for attrs in filters if attrs["aria-pressed"] == "true"], ["all"])
        covered = set()
        for card in cards:
            self.assertNotIn("hidden", card, "All content must be available without JavaScript")
            assigned = set(card["data-categories"].split())
            self.assertTrue(assigned)
            self.assertLessEqual(assigned, categories)
            covered.update(assigned)
        self.assertEqual(covered, categories)
        self.assertIn("hidden", elements["feature-controls"][1])
        self.assertIn("hidden", elements["feature-empty"][1])
        self.assertEqual(elements["feature-search"][1]["aria-controls"], "feature-catalogue")
        self.assertEqual(elements["feature-results"][1]["role"], "status")
        self.assertEqual(elements["feature-reset"][1]["type"], "button")
        self.assertTrue(any(tag == "label" and attrs.get("for") == "feature-search"
                            for tag, attrs in document.elements))
        for anchor in ("showcase", "clock", "sharing", "guides", "safety", "download", "questions", "resources",
                       "guide-start", "guide-backup", "guide-chat", "guide-group", "guide-nearby", "guide-export"):
            self.assertIn(anchor, document.ids)

    def test_screenshot_dimensions(self):
        import struct
        for name, height in (("library.png", 1031), ("review.png", 1031), ("members.png", 1059)):
            with (ROOT / "assets" / name).open("rb") as stream:
                header = stream.read(24)
            self.assertEqual(header[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", header[16:24]), (600, height))

    def test_text_palette_contrast(self):
        def luminance(color):
            channels = [int(color[i:i + 2], 16) / 255 for i in (0, 2, 4)]
            linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
            return sum(c * weight for c, weight in zip(linear, (0.2126, 0.7152, 0.0722)))
        for foreground, background in (("5d6573", "f6f7f9"), ("5d6573", "eceff5"),
                                       ("ffffff", "315bd6"), ("17377e", "e8eeff"),
                                       ("495363", "f6f7f9"), ("5d6573", "e8eeff"),
                                       ("c0c9d9", "273958"), ("b3c3ff", "273958"),
                                       ("f6f7f9", "344968"), ("495363", "e8ecf4")):
            light, dark = sorted((luminance(foreground), luminance(background)), reverse=True)
            self.assertGreaterEqual((light + 0.05) / (dark + 0.05), 4.5)

    @unittest.skipUnless(os.environ.get("SCV_ARTIFACTS"), "Set SCV_ARTIFACTS to check actual release assets.")
    def test_mismatched_release_assets_are_rejected(self):
        release = json.loads((ROOT / "release.json").read_text())
        directory = Path(os.environ["SCV_ARTIFACTS"])
        for key, value in (("apkBytes", release["apkBytes"] + 1),
                           ("apkSha256", "0" * 64), ("sourceSha256", "0" * 64)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                site_build.verify_artifacts(directory, {**release, key: value})

    @unittest.skipUnless(os.environ.get("SCV_ARTIFACTS"), "Set SCV_ARTIFACTS to check actual release assets.")
    def test_verified_builds_and_internal_links(self):
        build_root = ROOT.parent / "build"
        build_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="site-tests-", dir=build_root) as temporary:
            for repository, name in ((None, "preview"), ("example/secure-clock-vault", "public")):
                output = site_build.build(Path(os.environ["SCV_ARTIFACTS"]), Path(temporary) / name, repository)
                for page in ("index.html", "privacy.html"):
                    text = (output / page).read_text()
                    self.assertNotIn("{{", text)
                    document = Document(text)
                    for _, link in document.links:
                        parsed = urlsplit(link)
                        if parsed.scheme:
                            self.assertEqual(parsed.scheme, "https")
                            continue
                        target = output / unquote(parsed.path or page)
                        if target.is_dir():
                            target /= "index.html"
                        self.assertTrue(target.is_file(), f"Missing link target: {link}")
                        self.assertTrue(target.resolve().is_relative_to(output))
                        if parsed.path in ("assets/site.css", "assets/site.js"):
                            self.assertEqual(parse_qs(parsed.query), {"v": [site_build.sha256(target)[:12]]})
                        if parsed.fragment:
                            self.assertIn(unquote(parsed.fragment), Document(target.read_text()).ids)
                home = (output / "index.html").read_text()
                if repository:
                    self.assertIn("/releases/download/v3.20/SecureClockVault-release.apk", home)
                    self.assertIn("/releases/download/v3.20/SecureClockVault-3.20-source.zip", home)
                    self.assertNotIn("{{", home)
                else:
                    self.assertNotIn("/releases/download/", home)
                    self.assertIn("public downloads are not live", home)
                files = [item for item in output.rglob("*") if item.is_file()]
                self.assertLess(sum(item.stat().st_size for item in files), 3_000_000)
                self.assertFalse(any(item.suffix in (".apk", ".jks", ".zip", ".idsig") for item in files))
                self.assertFalse(any("password" in item.name for item in files))
                with self.assertRaises(FileExistsError):
                    site_build.build(Path(os.environ["SCV_ARTIFACTS"]), output, repository)


if __name__ == "__main__":
    unittest.main()
