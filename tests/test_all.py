import os, shutil, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from fvcore.exhaustive import forall, DomainTooLarge
from fvcore.intervals import Interval as I, poly_identity
from fvcore import certificate
from proofs import lemmas


class TestCore(unittest.TestCase):
    def test_forall_proves_and_refutes(self):
        self.assertTrue(forall("ok", {"a": range(10), "b": range(10)}, lambda a, b: a + b == b + a).ok())
        r = forall("bad", {"a": range(10)}, lambda a: a != 7)
        self.assertEqual(r.status, "REFUTED"); self.assertEqual(r.counterexample, {"a": 7})

    def test_exception_is_counterexample(self):
        r = forall("exc", {"a": range(3)}, lambda a: 1 // a == 1)
        self.assertFalse(r.ok()); self.assertIn("ZeroDivisionError", r.counterexample["__exception__"])

    def test_never_samples(self):
        with self.assertRaises(DomainTooLarge):
            forall("big", {"a": range(3000), "b": range(3000)}, lambda a, b: True, max_cases=1000)

    def test_intervals(self):
        self.assertTrue((I(0, 9999) * I(1, 10000) + I(0, 9999)).fits(64, False))
        self.assertFalse((I(0, 10**5) * I(0, 10**5)).fits(32, False))
        self.assertEqual(I(-3, 5).hi, 5)

    def test_poly_identity_detects_false(self):
        self.assertTrue(poly_identity(lambda a, b: (a + b) ** 2, lambda a, b: a * a + 2 * a * b + b * b, 2, 2))
        self.assertFalse(poly_identity(lambda a, b: (a + b) ** 2, lambda a, b: a * a + b * b, 2, 2))

    def test_certificate_hmac(self):
        c = certificate.build([{"status": "PROVEN"}], [__file__], key=b"k")
        self.assertTrue(certificate.verify_signature(c, b"k"))
        c["proofs"][0]["status"] = "REFUTED"
        self.assertFalse(certificate.verify_signature(c, b"k"))


class TestLemmas(unittest.TestCase):
    def test_all_proven(self):
        ps = lemmas.all_lemmas()
        self.assertEqual(len(ps), 8)
        for p in ps:
            self.assertTrue(p.ok(), p.name)

    def test_lemma_fails_when_range_grows_past_type(self):
        # con dimensiones de hasta 2^33 el producto ya no cabe en size_t: el lema debe REFUTARSE
        self.assertFalse(lemmas.index_in_bounds("x", 1 << 33, 1 << 33, "i*k+p").ok())


@unittest.skipUnless(shutil.which("gcc"), "requiere gcc")
class TestC(unittest.TestCase):
    def test_c_proofs_and_mutants(self):
        from proofs import run_c_exhaustive
        proofs, mut, _ = run_c_exhaustive.run(verbose=False)
        self.assertEqual(len(proofs), 4)
        self.assertTrue(all(p["status"] == "PROVEN" for p in proofs))
        self.assertEqual(mut["survived"], [], "un mutante sobrevivió: el arnés no detecta ese fallo")
        self.assertGreaterEqual(mut["total"], 14)

    def test_obligations_compile_and_run(self):
        from proofs import gen_obligations, smoke_cbmc
        gen_obligations.generate()
        res = smoke_cbmc.run()
        self.assertEqual(len(res), 8)
        for n, ok, msg in res:
            self.assertTrue(ok, f"{n}: {msg}")


class TestAutohealFormal(unittest.TestCase):
    def test_tricky_rejected_good_accepted(self):
        sys.path.insert(0, os.path.join(ROOT, "examples"))
        import demo_autoheal_formal as d
        from integration.formal_autoheal import FormalVerifier
        from autoheal import SubprocessVerifier
        fv = FormalVerifier({"mean": d.PROOF})
        self.assertTrue(SubprocessVerifier().verify(d.TRICKY, d.SPEC).ok)       # el verificador aleatorio lo deja pasar
        r = fv.verify(d.TRICKY, d.SPEC)
        self.assertFalse(r.ok); self.assertIn("REFUTADA", r.failures[0])
        g = fv.verify(d.GOOD, d.SPEC)
        self.assertTrue(g.ok); self.assertTrue(all(p["status"] == "PROVEN" for p in g.proofs)); self.assertEqual(len(g.proofs), 5)

    def test_missing_proof_is_rejected_by_default(self):
        sys.path.insert(0, os.path.join(ROOT, "examples"))
        import demo_autoheal_formal as d
        from integration.formal_autoheal import FormalVerifier
        self.assertFalse(FormalVerifier({}).verify(d.GOOD, d.SPEC).ok)
        self.assertTrue(FormalVerifier({}, require_proof=False).verify(d.GOOD, d.SPEC).ok)

    def test_infinite_loop_candidate_times_out(self):
        sys.path.insert(0, os.path.join(ROOT, "examples"))
        import demo_autoheal_formal as d
        from integration.formal_autoheal import FormalVerifier
        hang = "def mean(xs):\n    while True:\n        pass\n"
        self.assertFalse(FormalVerifier({"mean": d.PROOF}, timeout_s=1).verify(hang, d.SPEC).ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
