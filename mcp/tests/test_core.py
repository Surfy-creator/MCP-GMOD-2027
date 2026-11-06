import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gmod_hammer_mcp import vmf, fgd, logic, compile as comp  # noqa: E402

HERE = Path(__file__).parent

FGD_SRC = """
@BaseClass = Targetname
[
    targetname(target_source) : "Name"
    input Kill(void) : "Remove"
]
@PointClass base(Targetname) = my_ent : "Desc"
[
    speed(float) : "Speed" : 10
    output OnX(void) : "Fired"
]
"""


class T(unittest.TestCase):
    def test_vmf(self):
        r = vmf.analyze(HERE / "sample.vmf")
        self.assertEqual(r["world_brushes"], 1)
        self.assertEqual(r["tool_textures"]["nodraw"], 1)
        self.assertEqual(r["io"]["broken_connection_count"], 1)
        self.assertEqual(r["io"]["dangling_key_count"], 1)
        self.assertEqual(r["spawns"], 1)

    def test_split_output(self):
        self.assertEqual(logic.split_output("a,Open,,2.5,1"), ("a", "Open", "", 2.5, 1))
        self.assertEqual(logic.split_output("a\x1bOpen\x1b\x1b0\x1b-1")[0], "a")

    def test_fgd(self):
        r = fgd.resolve(fgd.parse_text(FGD_SRC), "my_ent")
        self.assertIn("speed", r["keys"])
        self.assertIn("targetname", r["keys"])
        self.assertIn("Kill", r["inputs"])
        self.assertIn("OnX", r["outputs"])

    def test_plan(self):
        env = {"vbsp": "vbsp", "vvis": "vvis", "vrad": "vrad", "gamedir": "g", "maps_dir": "m"}
        p = comp.plan(env, "x/map.vmf", "fast")
        self.assertEqual([s["tool"] for s in p["steps"][:3]], ["vbsp", "vvis", "vrad"])
        self.assertEqual(len(comp.plan(env, "x/map.vmf", "entities_only")["steps"]), 2)
        self.assertTrue(p["steps"][0]["cmd"][-1].endswith("map.vmf"))
        self.assertFalse(p["steps"][1]["cmd"][-1].endswith(".vmf"))

    def test_log(self):
        self.assertTrue(comp.parse_log("Entity info_player_start (0 0 0) leaked!\n*** leaked ***")["leaked"])


if __name__ == "__main__":
    unittest.main()
