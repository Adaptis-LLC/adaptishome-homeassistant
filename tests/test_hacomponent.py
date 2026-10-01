"""Інтеграція Home Assistant (custom_components/adaptishome) без самого HA: маніфест, переклади, ключі сутностей."""
import json, os, re, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "custom_components", "adaptishome")


def src(name):
    with open(os.path.join(D, name), encoding="utf-8") as f: return f.read()


class HaComponentTest(unittest.TestCase):
    def test_manifest_and_hacs(self):
        m = json.load(open(os.path.join(D, "manifest.json")))
        self.assertEqual((m["domain"], m["config_flow"], m["iot_class"], m["requirements"]), ("adaptishome", True, "cloud_polling", []))
        self.assertTrue(re.fullmatch(r"\d+\.\d+\.\d+", m["version"]))
        self.assertEqual(json.load(open(os.path.join(ROOT, "hacs.json")))["name"], "AdaptisHome")

    def test_translations_cover_entities(self):
        # кожен translation_key із коду має назву в strings.json і в українському перекладі; обидві мови — однакові ключі
        en, uk = json.load(open(os.path.join(D, "strings.json"))), json.load(open(os.path.join(D, "translations", "uk.json")))
        self.assertEqual(json.load(open(os.path.join(D, "translations", "en.json"))), en)
        def keys(d, p=""):
            return {p + k for k, v in d.items() if not isinstance(v, dict)} | set().union(*(keys(v, p + k + ".") for k, v in d.items() if isinstance(v, dict)))
        self.assertEqual(keys(en), keys(uk))
        sensors = set(re.findall(r'ObjDesc\(key="(\w+)"', src("sensor.py")))
        channels = {"channel_" + k for k in re.findall(r'ChDesc\(key="(\w+)"', src("sensor.py"))}
        self.assertTrue(sensors and channels)
        self.assertEqual(sensors | channels, set(en["entity"]["sensor"]))
        self.assertEqual(set(en["entity"]["binary_sensor"]), {"online", "failover", "channel_ready"})
        self.assertEqual(set(en["entity"]["event"]), {"event"})
        for s in ("STATUSES", "CH_STATES"):
            opts = set(re.search(s + r' = \[([^\]]+)\]', src("sensor.py"))[1].replace('"', "").replace(" ", "").split(","))
            name = "status" if s == "STATUSES" else "channel_state"
            self.assertEqual(opts, set(en["entity"]["sensor"][name]["state"]))
        self.assertEqual(set(re.search(r'_attr_event_types = \[([^\]]+)\]', src("event.py"))[1].replace('"', "").replace(" ", "").split(",")),
                         set(en["entity"]["event"]["event"]["state_attributes"]["event_type"]["state"]))

    def test_api_uses_only_documented_endpoints(self):
        self.assertEqual(set(re.findall(r'/api/[a-z_/]+', src("api.py"))), {"/api/login", "/api/devices", "/api/device"})


if __name__ == "__main__":
    unittest.main()
