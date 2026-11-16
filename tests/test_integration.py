#!/usr/bin/env python3
"""Testy integrácie Samsung Heat Pump AI Control bez Home Assistanta: čistá logika (model.py), syntax, JSON, preklady.

Spustenie z koreňa repozitára:  python -X utf8 -m unittest discover -s tests -v
(test zhody ciest so serverom sa spustí, len ak KURENIE_APP ukazuje na priečinok aplikácie)
"""
import importlib.util, json, os, py_compile, re, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMP = os.path.join(ROOT, "custom_components", "samsung_heat_pump_ai_control")

spec = importlib.util.spec_from_file_location("kurenie_model", os.path.join(COMP, "model.py"))
model = importlib.util.module_from_spec(spec)
sys.modules["kurenie_model"] = model     # dataclass/typing potrebujú modul v sys.modules
spec.loader.exec_module(model)


def load(name):
    with open(os.path.join(COMP, name), encoding="utf-8") as f:
        return json.load(f)


def state():
    return {
        "api": 1, "verzia": "2.3.0", "ts": 1,
        "zariadenie": {"nazov": "Samsung EHS Mono", "model": "AE080", "typ": "mono", "vykon_kw": 8.0, "kurenie": "podlahove"},
        "izby": [{"kluc": "obyvacka", "nazov": "Obývačka", "teplota": 22.4, "min": None, "referencna": True},
                 {"kluc": "kuchyna", "nazov": "Kuchyňa", "teplota": None, "min": 21.0, "referencna": False}],
        "vonku": 3.4, "ciel_izba": 23.5, "ciel_rozsah": [19.0, 24.0], "posun": -1,
        "voda": {"vystup": 35.2, "spiatocka": 31.1, "ciel_krivky": 33, "delta_t": 4.1},
        "kompresor": {"frekvencia": 40, "bezi": True, "odmrazovanie": False},
        "tuv": {"teplota": 47.0, "ciel": 48.0, "ohrev_bezi": True},
        "agent": {"rezim": "control", "posledny_beh": 5, "stav": "pozor", "zhrnutie": "x" * 400, "dalsi_beh": 9},
        "chyba_tc": 0, "poplachy": [{"druh": "okno", "text": "Okno"}],
        "online": {"esp": True, "zberac": True, "ha": None},
    }


class Hodnoty(unittest.TestCase):
    def test_senzory(self):
        s = state()
        v = {k: fn(s) for k, fn in model.SENSORS.items()}
        self.assertEqual(v["outdoor_temperature"], 3.4)
        self.assertEqual(v["water_out"], 35.2)
        self.assertEqual(v["water_return"], 31.1)
        self.assertEqual(v["water_target"], 33)
        self.assertEqual(v["water_delta_t"], 4.1)
        self.assertEqual(v["compressor_frequency"], 40)
        self.assertEqual(v["curve_offset"], -1)
        self.assertEqual(v["dhw_temperature"], 47.0)
        self.assertEqual(v["error_code"], 0)
        self.assertEqual(v["agent_state"], "pozor")
        self.assertEqual(len(v["agent_summary"]), 255)
        self.assertEqual(v["alert_count"], 1)
        self.assertEqual(len(model.agent_attributes(s)["summary"]), 400)    # celý text je v atribúte
        self.assertEqual(model.alert_attributes(s)["alerts"], [{"kind": "okno", "text": "Okno"}])

    def test_binarne(self):
        s = state()
        v = {k: fn(s) for k, fn in model.BINARY_SENSORS.items()}
        self.assertIs(v["compressor_running"], True)
        self.assertIs(v["defrost"], False)
        self.assertIs(v["dhw_heating"], True)
        self.assertIs(v["problem"], True)           # poplach
        self.assertIs(v["esp_online"], True)
        self.assertIsNone(model.bool_or_none(v["ha_online"]))

    def test_problem(self):
        s = state()
        s["poplachy"] = []
        self.assertFalse(model.problem(s))
        s["chyba_tc"] = 5
        self.assertTrue(model.problem(s))
        s["chyba_tc"] = None
        self.assertFalse(model.problem(s))

    def test_chybajuce_a_zle_hodnoty(self):
        for s in ({"api": 1}, {"api": 1, "voda": None, "kompresor": "x", "agent": [], "izby": "x", "poplachy": "x"}):
            for fn in model.SENSORS.values():
                fn(s)                                # nesmie spadnúť
            for fn in model.BINARY_SENSORS.values():
                fn(s)
            self.assertIsNone(model.SENSORS["water_out"](s))
            self.assertIsNone(model.agent_mode(s))
            self.assertEqual(model.rooms(s), [])
            self.assertFalse(model.has_dhw(s))
            self.assertEqual(model.room_target_range(s), model.ROOM_RANGE_FALLBACK)
        self.assertIsNone(model.SENSORS["agent_state"]({"agent": {"stav": "inak"}}))
        self.assertIsNone(model._num(True))

    def test_izby(self):
        s = state()
        self.assertEqual(model.room_temperature(s, "obyvacka"), 22.4)
        self.assertIsNone(model.room_temperature(s, "kuchyna"))
        self.assertEqual(model.room_attributes(s, "kuchyna"), {"min_target": 21.0, "reference": False})
        self.assertEqual(model.room_name(s, "obyvacka"), "Obývačka")

    def test_tuv(self):
        s = state()
        self.assertTrue(model.has_dhw(s))
        s["tuv"] = None
        self.assertFalse(model.has_dhw(s))

    def test_rozsah_a_zariadenie(self):
        s = state()
        self.assertEqual(model.room_target_range(s), (19.0, 24.0))
        self.assertEqual(model.room_target(s), 23.5)
        self.assertEqual(model.device_info(s), {"name": "Samsung Heat Pump AI Control", "model": "AE080", "sw_version": "2.3.0"})
        self.assertEqual(model.device_info({})["name"], "Samsung Heat Pump AI Control")
        self.assertEqual(model.entry_title(s), "Samsung Heat Pump AI Control – Samsung EHS Mono")
        self.assertEqual(model.entry_title({}), "Samsung Heat Pump AI Control")
        self.assertTrue(model.validate_state(s))
        self.assertFalse(model.validate_state({"api": 2}))
        self.assertFalse(model.validate_state([]))


class Akcie(unittest.TestCase):
    def test_mapovanie(self):
        self.assertEqual(model.action_mode("off"), ("/api/ha/v1/mode", {"mode": "off"}))
        self.assertEqual(model.action_room_target(22.74), ("/api/ha/v1/room_target", {"value": 22.5}))
        self.assertEqual(model.action_room_target(23), ("/api/ha/v1/room_target", {"value": 23.0}))
        self.assertEqual(model.action_run_now(), ("/api/ha/v1/run_now", {}))
        self.assertEqual(model.action_tuv_boost(), ("/api/ha/v1/tuv_boost", {}))
        with self.assertRaises(ValueError):
            model.action_mode("zle")

    def test_cesty_zodpovedaju_serveru(self):
        # ha_api.py je v repozitári aplikácie; nastav KURENIE_APP na jeho priečinok
        app = os.environ.get("KURENIE_APP", "")
        if not os.path.isfile(os.path.join(app, "ha_api.py")):
            self.skipTest("KURENIE_APP neukazuje na priečinok aplikácie s ha_api.py")
        sys.path.insert(0, app)
        import ha_api
        for p in (model.API_MODE, model.API_ROOM_TARGET, model.API_TUV_BOOST, model.API_RUN_NOW):
            self.assertIn(p, ha_api.ACTIONS)
        self.assertEqual(model.API_STATE, ha_api.PATH_STATE)
        for fn in (lambda: model.action_mode("advise"), lambda: model.action_room_target(21), model.action_tuv_boost, model.action_run_now):
            path, body = fn()
            self.assertTrue(ha_api.validate_action(path, body)[0], path)


class Pomocne(unittest.TestCase):
    def test_url(self):
        n = model.normalize_url
        self.assertEqual(n("192.168.1.50"), "http://192.168.1.50")
        self.assertEqual(n(" http://192.168.1.50/ "), "http://192.168.1.50")
        self.assertEqual(n("https://kurenie.example.com:8443/x/y"), "https://kurenie.example.com:8443")
        self.assertEqual(n("http://[::1]:8080"), "http://[::1]:8080")
        for bad in ("", "   ", "ftp://x", "http://", "http://h:99999"):
            with self.assertRaises(ValueError, msg=bad):
                n(bad)

    def test_interval(self):
        c = model.clamp_interval
        self.assertEqual((c(None), c("x"), c(5), c(1000), c(60), c(30.7)), (30, 30, 15, 300, 60, 30))


class Subory(unittest.TestCase):
    def test_syntax(self):
        files = [os.path.join(COMP, f) for f in os.listdir(COMP) if f.endswith(".py")]
        self.assertGreaterEqual(len(files), 10)
        with tempfile.TemporaryDirectory() as d:
            for i, f in enumerate(files):
                py_compile.compile(f, cfile=os.path.join(d, "%d.pyc" % i), doraise=True)

    def test_json(self):
        for rel in ("manifest.json", "strings.json", "translations/sk.json", "translations/en.json", "../../hacs.json"):
            load(rel)
        m = load("manifest.json")
        self.assertEqual(m["domain"], "samsung_heat_pump_ai_control")
        self.assertTrue(m["config_flow"])
        self.assertEqual(m["iot_class"], "local_polling")
        self.assertRegex(m["version"], r"^\d+\.\d+\.\d+$")
        self.assertEqual(m["codeowners"], ["@soso8782"])
        h = load("../../hacs.json")
        self.assertEqual((h["name"], h["render_readme"]), ("Samsung Heat Pump AI Control", True))

    def test_preklady(self):
        def keys(d, p=""):
            out = set()
            for k, v in d.items():
                out |= keys(v, p + k + ".") if isinstance(v, dict) else {p + k}
            return out
        s, en, sk = (keys(load(f)) for f in ("strings.json", "translations/en.json", "translations/sk.json"))
        self.assertEqual(s, en)
        self.assertEqual(s, sk)
        self.assertEqual(load("strings.json"), load("translations/en.json"))

    def test_translation_keys_existuju(self):
        t = load("strings.json")["entity"]
        used = {}
        for plat, fname in (("sensor", "sensor.py"), ("binary_sensor", "binary_sensor.py"), ("select", "select.py"),
                            ("number", "number.py"), ("button", "button.py")):
            with open(os.path.join(COMP, fname), encoding="utf-8") as f:
                src = f.read()
            used[plat] = set(re.findall(r'translation_key\s*=\s*"([a-z_]+)"', src))
            self.assertTrue(used[plat], plat)
            self.assertEqual(used[plat] - set(t[plat]), set(), plat)
        # každý kľúč senzorov a binárnych senzorov z model.py má popis aj preklad
        self.assertEqual(set(model.SENSORS) - used["sensor"], set())
        self.assertEqual(set(model.BINARY_SENSORS) - used["binary_sensor"], set())
        ex = load("strings.json")["exceptions"]
        with open(os.path.join(COMP, "coordinator.py"), encoding="utf-8") as f:
            for k in re.findall(r'translation_key="([a-z_]+)"', f.read()):
                self.assertIn(k, ex)

    def test_stavy_agenta_v_prekladoch(self):
        t = load("strings.json")["entity"]
        self.assertEqual(set(t["sensor"]["agent_state"]["state"]), set(model.AGENT_STATES))
        self.assertEqual(set(t["select"]["agent_mode"]["state"]), set(model.MODES))


if __name__ == "__main__":
    unittest.main()
