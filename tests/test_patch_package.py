import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import warnings
from pathlib import Path
from zipfile import ZipFile

SPEC = importlib.util.spec_from_file_location("patch_package", Path(__file__).resolve().parents[1] / "tools" / "patch_package.py")
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)
# Load the actual forward-check helper with the same package module.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from check_forward_packages import package_base, component_target


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Fixture")
        for c, (launcher, marker, name, family, _) in p.COMPONENTS.items():
            v = (*family, 1)
            self.write(c + "/" + launcher, "print('launcher')\n")
            self.write(c + "/" + marker, self.marker(c, v))
            self.write(p.note_path(c,v), "prior note\n")
        self.base = self.commit("base")
        self.c = "PiSD"
        self.write("PiSD/pisd/__init__.py", self.marker(self.c,(0,11,2)))
        self.write("PiSD/pisd/new.py", "VALUE = 42\n")
        self.write(p.note_path(self.c,(0,11,2)), "new note\n")
        self.target = self.commit("target")
        self.archive = self.root / "patch.zip"
        self.git("checkout","--detach",self.base)

    def marker(self,c,v):
        name = p.COMPONENTS[c][2]
        s = ".".join(map(str,v))
        if c == "PiServer":
            s = s.replace(".","_")
        return f"{name} = {s!r}\n" + (f"PATCH_VERSION = {'piTrainer_'+s.replace('.','_')!r}\n" if c=="piTrainer" else "")

    def git(self,*args):
        return subprocess.check_output(["git","-C",str(self.root),*args],stderr=subprocess.PIPE).decode().strip()

    def write(self,path,content):
        dest = self.root / path
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(content,encoding="utf-8")

    def commit(self,msg):
        self.git("add",".")
        self.git("commit","-qm",msg)
        return self.git("rev-parse","HEAD")

    def build(self):
        return p.build(self.root,self.c,self.base,self.target,self.archive)

    def validate(self):
        return p.validate(self.root,self.c,self.base,self.target,self.archive)

    def rewrite(self, transform):
        with ZipFile(self.archive) as z:
            entries = [(i.filename,z.read(i)) for i in z.infolist()]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore",UserWarning)
            with ZipFile(self.archive,"w") as z:
                for name,data in transform(entries):
                    z.writestr(name,data)

    def test_forward_and_no_writes(self):
        m = self.build()
        self.assertEqual(m,self.validate())
        self.assertEqual(set(m["files"]),{"PiSD/pisd/__init__.py","PiSD/pisd/new.py",p.note_path(self.c,(0,11,2))})
        self.assertFalse((self.root/"PiSD/pisd/new.py").exists())
        self.assertEqual(self.git("rev-parse","HEAD"),self.base)

    def test_stale_checkout(self):
        self.build()
        self.git("checkout","--detach",self.target)
        with self.assertRaisesRegex(ValueError,"Stale"):
            self.validate()

    def test_wrong_component(self):
        self.build()
        with self.assertRaises(ValueError):
            p.validate(self.root,"PiServer",self.base,self.target,self.archive)

    def test_extra_duplicate_traversal_and_tampering(self):
        for name in ("PiServer/server.py","../evil","PiSD/config/runtime.json","PiSD/pisd/new.py"):
            with self.subTest(name=name):
                if self.archive.exists():
                    self.archive.unlink()
                self.build()
                self.rewrite(lambda entries: entries+[(name,b"x")])
                with self.assertRaises(ValueError):
                    self.validate()
        self.archive.unlink()
        self.build()
        self.rewrite(lambda entries:[(n,b"bad" if n.endswith("new.py") else d) for n,d in entries])
        with self.assertRaises(ValueError):
            self.validate()

    def test_manifest_tampering(self):
        self.build()
        def edit(entries):
            result=[]
            for n,d in entries:
                if n==p.MANIFEST:
                    m=json.loads(d)
                    m["component"]="PiServer"
                    d=p.encoded(m)
                result.append((n,d))
            return result
        self.rewrite(edit)
        with self.assertRaises(ValueError):
            self.validate()

    def test_local_change_and_new_collision(self):
        self.build()
        self.write("PiSD/pisd/new.py","local")
        with self.assertRaisesRegex(ValueError,"already exists"):
            self.validate()
        (self.root/"PiSD/pisd/new.py").unlink()
        self.write("PiSD/PiSD.py","changed")
        with self.assertRaisesRegex(ValueError,"Locally modified"):
            self.validate()

    def test_forbidden_git_changes(self):
        for path in ("PiSD/config/runtime.json","PiSD/pisd/__pycache__/x.pyc",
                     "PiSD/models/model.tflite","PiSD/recordings/private.jpg",
                     "PiSD/pisd/credentials.py"):
            with self.subTest(path=path):
                self.git("checkout","--detach",self.target)
                self.write(path,"not distributable")
                bad=self.commit("bad")
                with self.assertRaisesRegex(ValueError,"Forbidden"):
                    p.expected(self.root,self.c,self.base,bad)

    def test_only_reviewed_trainer_checkbox_svgs_are_distributable(self):
        path = "piTrainer/piTrainer/ui/checkbox_check.svg"
        light_path = "piTrainer/piTrainer/ui/checkbox_check_light.svg"
        self.assertTrue(p.allowed("piTrainer", path))
        self.assertTrue(p.allowed("piTrainer", light_path))
        for forbidden in ("piTrainer/piTrainer/ui/other.svg",
                          "piTrainer/config/checkbox_check.svg",
                          "piTrainer/piTrainer/ui/../checkbox_check.svg",
                          "PiSD/pisd/checkbox_check.svg"):
            self.assertFalse(p.allowed("piTrainer", forbidden))
        self.assertFalse(p.allowed("PiSD", "PiSD/pisd/checkbox_check.svg"))
        self.c = "piTrainer"
        self.write("piTrainer/piTrainer/version.py", self.marker(self.c, (0, 11, 2)))
        self.write(p.note_path(self.c, (0, 11, 2)), "new note")
        self.write(path, '<svg xmlns="http://www.w3.org/2000/svg"/>')
        self.write(light_path, '<svg xmlns="http://www.w3.org/2000/svg"/>')
        self.target = self.commit("reviewed static asset")
        self.git("checkout", "--detach", self.base)
        manifest = self.build()
        self.assertEqual(manifest, self.validate())
        self.assertEqual(manifest["files"][path]["operation"], "A")
        self.assertEqual(manifest["files"][light_path]["operation"], "A")
        self.assertFalse((self.root / light_path).exists())
        self.assertFalse((self.root / path).exists())
        self.git("checkout", "--detach", self.target)
        self.write("piTrainer/piTrainer/ui/other.svg", "<svg/>")
        bad = self.commit("unapproved asset")
        with self.assertRaisesRegex(ValueError, "Forbidden"):
            p.expected(self.root, self.c, self.base, bad)

    def test_each_other_component(self):
        for c in ("PiServer","piTrainer"):
            with self.subTest(component=c):
                self.git("checkout","--detach",self.base)
                _,marker,_,family,_=p.COMPONENTS[c]
                v=(*family,2)
                self.write(c+"/"+marker,self.marker(c,v))
                self.write(p.note_path(c,v),"new note")
                target=self.commit("forward")
                archive=self.root/(c+".zip")
                p.build(self.root,c,self.base,target,archive)
                self.git("checkout","--detach",self.base)
                self.assertEqual(p.validate(self.root,c,self.base,target,archive)["component"],c)

    def test_historical_source_reintroduction(self):
        self.write("PiSD/PiSD.py", "print('newer launcher')\n")
        newer = self.commit("accepted source improvement")
        self.write("PiSD/PiSD.py", "print('launcher')\n")
        self.write("PiSD/pisd/__init__.py", self.marker(self.c,(0,11,2)))
        self.write(p.note_path(self.c,(0,11,2)), "new note\n")
        rollback = self.commit("accidental old source")
        with self.assertRaisesRegex(ValueError,"Exact historical file rollback"):
            p.expected(self.root,self.c,newer,rollback)

    def test_historical_note_change(self):
        self.git("checkout","--detach",self.target)
        self.write(p.note_path(self.c,(0,11,1)),"rewritten")
        target=self.commit("bad history")
        with self.assertRaisesRegex(ValueError,"Historical note"):
            p.expected(self.root,self.c,self.base,target)


    def test_stacked_package_base_includes_pre_version_source_changes(self):
        self.write("PiServer/piserver/app.py", self.marker("PiServer", (0,4,1)) + "VALUE = 2\n")
        staged = self.commit("source checkpoint")
        self.write("PiServer/piserver/app.py", self.marker("PiServer", (0,4,2)) + "VALUE = 2\n")
        self.write(p.note_path("PiServer",(0,4,2)), f"Package baseline: {self.base}\n")
        target = self.commit("allocate candidate")
        self.assertEqual(package_base(self.root, target, "PiServer"), self.base)
        manifest, _ = p.expected(self.root, "PiServer", self.base, target)
        self.assertIn("PiServer/piserver/app.py", manifest["files"])
        self.assertNotEqual(staged, self.base)

    def test_marker_file_edit_without_version_change_resolves_actual_bump(self):
        self.git("checkout","--detach",self.target)
        self.write("PiSD/pisd/__init__.py", self.marker("PiSD",(0,11,2)) + "VALUE = 3\n")
        touched = self.commit("ordinary code edit")
        self.assertEqual(package_base(self.root, touched, "PiSD"), self.base)

    def test_inherited_source_only_for_identical_component_tree(self):
        self.git("checkout","--detach",self.base)
        self.write("PiServer/README.md", "unrelated branch content")
        other = self.commit("other parent")
        self.git("checkout","--detach",self.target)
        self.write("PiSD/README.md", "new component content")
        changed = self.commit("candidate change")
        self.assertEqual(component_target(self.root, changed, "PiSD", self.target), changed)
        self.assertEqual(component_target(self.root, changed, "PiServer", self.target), self.target)
        self.assertEqual(component_target(self.root, changed, "PiServer"), changed)
        with self.assertRaisesRegex(ValueError,"ancestor"):
            component_target(self.root, changed, "PiServer", other)

    def test_explicit_v1_transition_and_first_patch(self):
        for c, previous in p.V1_BASELINES.items():
            with self.subTest(component=c):
                self.git("checkout", "--detach", self.base)
                _, marker, _, _, _ = p.COMPONENTS[c]
                self.write(c + "/" + marker, self.marker(c, previous))
                self.write(p.note_path(c, previous), "qualified prior candidate")
                legacy = self.commit("legacy candidate")
                self.write(c + "/" + marker, self.marker(c, (1, 0, 0)))
                self.write(p.note_path(c, (1, 0, 0)), f"Package baseline: {legacy}\n")
                bad = self.commit("missing transition declaration")
                with self.assertRaisesRegex(ValueError, "Unauthorized"):
                    p.expected(self.root, c, legacy, bad)
                with self.assertRaisesRegex(ValueError, "forward"):
                    package_base(self.root, bad, c)
                previous_text = ".".join(map(str, previous))
                self.write(p.note_path(c, (1, 0, 0)),
                           f"Package baseline: {legacy}\nRelease transition: {previous_text} -> 1.0.0\n")
                promoted = self.commit("explicit release candidate")
                self.assertEqual(package_base(self.root, promoted, c), legacy)
                archive = self.root / (c + "-v1.zip")
                p.build(self.root, c, legacy, promoted, archive)
                self.git("checkout", "--detach", legacy)
                self.assertEqual(p.validate(self.root, c, legacy, promoted, archive)["target_version"], "1.0.0")
                self.git("checkout", "--detach", promoted)
                self.write(c + "/" + marker, self.marker(c, (1, 0, 1)))
                self.write(p.note_path(c, (1, 0, 1)), "forward patch")
                patched = self.commit("v1 patch")
                self.assertEqual(package_base(self.root, patched, c), promoted)
                p.expected(self.root, c, promoted, patched)
                self.write(c + "/" + marker, self.marker(c, (1, 1, 0)))
                invalid = self.commit("unauthorized family")
                with self.assertRaisesRegex(ValueError, "Wrong version family"):
                    p.version(self.root, invalid, c)

    def test_package_base_rejects_same_version_or_malformed_declaration(self):
        self.git("checkout","--detach",self.target)
        self.write(p.note_path("PiSD",(0,11,2)), f"Package baseline: {self.target}\n")
        bad = self.commit("same version")
        with self.assertRaisesRegex(ValueError, "forward"):
            package_base(self.root, bad, "PiSD")
        self.write(p.note_path("PiSD",(0,11,2)), "Package baseline: not-a-sha\n")
        bad = self.commit("malformed")
        with self.assertRaisesRegex(ValueError, "Invalid"):
            package_base(self.root, bad, "PiSD")


if __name__ == "__main__":
    unittest.main()
