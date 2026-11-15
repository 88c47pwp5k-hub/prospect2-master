#!/usr/bin/env python3
"""
Suite de l'onglet Comptabilité de Prospect 2.0.

Elle pose sa propre condition de départ : chaque test écrit dans un fichier
jetable passé EXPLICITEMENT, jamais dans le vrai `data/comptabilite.json`.
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ICI))

import comptabilite as C                                        # noqa: E402
import prospect2_server as S                                    # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp(prefix="compta-essai-")
        self.fichier = os.path.join(self.dossier, "comptabilite.json")
        # Le serveur Flask lit par la variable d'environnement.
        os.environ["PROSPECT2_COMPTA"] = self.fichier

    def tearDown(self):
        os.environ.pop("PROSPECT2_COMPTA", None)

    def revenu(self, **kw):
        champs = {"date": "2026-11-10", "client": "Marchand", "avant_taxes": "150",
                  "activite": "decopatio", "description": "Fiche Premium"}
        champs.update(kw)
        return C.ajouter_revenu(champs, self.fichier)

    def depense(self, **kw):
        champs = {"date": "2026-11-10", "fournisseur": "Hébergeur",
                  "avant_taxes": "100", "activite": "general"}
        champs.update(kw)
        return C.ajouter_depense(champs, self.fichier)


# ── 1. Les libellés : « Prospect 2.0 / <activité> » partout ────────────────
class TestLibelles(Base):

    def test_les_trois_libelles_exacts(self):
        self.assertEqual(C.ACTIVITES["decopatio"], "Prospect 2.0 / DécoPatio")
        self.assertEqual(C.ACTIVITES["nano"],      "Prospect 2.0 / Nano Protection")
        self.assertEqual(C.ACTIVITES["general"],   "Prospect 2.0 / Général")

    def test_a_preciser_reste_tel_quel(self):
        """Décision de Benoit : « à préciser » ne porte pas le nom de la
        compagnie — ce n'est pas une activité, c'est l'absence de décision."""
        self.assertEqual(C.ACTIVITES[C.A_PRECISER], "à préciser")
        self.assertNotIn("Prospect", C.ACTIVITES[C.A_PRECISER])

    def test_aucune_marque_nue(self):
        """Aucune activité choisissable ne s'affiche sans la compagnie devant."""
        for code in C.ACTIVITES_CHOISISSABLES:
            self.assertTrue(C.ACTIVITES[code].startswith("Prospect 2.0 / "),
                            "%s ne commence pas par la compagnie" % code)

    def test_code_inconnu_ne_devine_pas_une_marque(self):
        self.assertEqual(C.libelle_activite("decopatioo"), "à préciser")
        self.assertEqual(C.libelle_activite(None), "à préciser")

    def test_libelle_dans_le_sommaire_et_les_lignes(self):
        self.revenu(activite="nano")
        self.depense(activite="decopatio")
        s = C.sommaire("2026-2027", date(2026, 11, 15), self.fichier)
        libelles = [v["libelle"] for v in s["ventilation"]]
        self.assertEqual(libelles, ["Prospect 2.0 / DécoPatio",
                                    "Prospect 2.0 / Nano Protection",
                                    "Prospect 2.0 / Général", "à préciser"])
        self.assertEqual(s["revenus"][0]["activite_libelle"],
                         "Prospect 2.0 / Nano Protection")
        self.assertEqual(s["depenses"][0]["activite_libelle"],
                         "Prospect 2.0 / DécoPatio")

    def test_libelle_dans_l_export(self):
        self.revenu(activite="general")
        lignes = C.lignes_export("2026-2027", date(2026, 11, 15), self.fichier)
        self.assertEqual(lignes[0][3], "Prospect 2.0 / Général")

    def test_boutons_de_classement_portent_la_compagnie(self):
        """Les trois boutons offerts à l'écran viennent de la même source."""
        s = C.sommaire("2026-2027", date(2026, 11, 15), self.fichier)
        self.assertEqual([a["libelle"] for a in s["activites"]],
                         ["Prospect 2.0 / DécoPatio", "Prospect 2.0 / Nano Protection",
                          "Prospect 2.0 / Général"])
        self.assertNotIn(C.A_PRECISER, [a["code"] for a in s["activites"]])


# ── 2. Aucun rétroactif ────────────────────────────────────────────────────
class TestDepartANeuf(Base):

    def test_exercice_dune_date(self):
        self.assertEqual(C.exercice_de(date(2026, 10, 31)), "2025-2026")
        self.assertEqual(C.exercice_de(date(2026, 11, 1)),  "2026-2027")
        self.assertEqual(C.exercice_de(date(2027, 10, 31)), "2026-2027")
        self.assertEqual(C.exercice_de(date(2027, 11, 1)),  "2027-2028")

    def test_le_selecteur_ne_propose_rien_avant(self):
        self.assertEqual(C.exercices_disponibles(date(2026, 11, 15)), ["2026-2027"])
        self.assertEqual(C.exercices_disponibles(date(2027, 11, 2)),
                         ["2026-2027", "2027-2028"])

    def test_une_piece_anterieure_est_refusee(self):
        with self.assertRaises(ValueError) as e:
            self.revenu(date="2026-10-31")
        self.assertIn("rétroactif", str(e.exception))
        with self.assertRaises(ValueError):
            self.depense(date="2025-08-27")

    def test_le_premier_jour_passe(self):
        ligne = self.revenu(date="2026-11-01")
        self.assertEqual(ligne["exercice"], "2026-2027")


# ── 3. Taxes ───────────────────────────────────────────────────────────────
class TestTaxes(Base):

    def test_tps_et_tvq(self):
        self.assertEqual(C.taxes_de(150.0), (7.50, 14.96))
        self.assertEqual(C.taxes_de(1000.0), (50.0, 99.75))

    def test_non_taxable(self):
        self.assertEqual(C.taxes_de(150.0, taxable=False), (0.0, 0.0))
        ligne = self.revenu(taxable=False)
        self.assertEqual((ligne["tps"], ligne["tvq"], ligne["total"]), (0.0, 0.0, 150.0))

    def test_montant_invalide_refuse_plutot_que_zero(self):
        for mauvais in ("", "abc", None, "12,34,56"):
            with self.assertRaises(ValueError):
                self.revenu(avant_taxes=mauvais)
        with self.assertRaises(ValueError):
            self.revenu(avant_taxes="-50")

    def test_virgule_decimale_acceptee(self):
        ligne = self.revenu(avant_taxes="1 234,56")
        self.assertEqual(ligne["avant_taxes"], 1234.56)

    def test_trimestre_a_venir_rend_none_pas_zero(self):
        """Zéro voudrait dire « vérifié, rien trouvé »."""
        s = C.sommaire("2026-2027", date(2026, 11, 15), self.fichier)
        t1, t2 = s["taxes"][0], s["taxes"][1]
        self.assertFalse(t1["a_venir"])
        self.assertEqual(t1["net"], 0.0)
        self.assertTrue(t2["a_venir"])
        self.assertIsNone(t2["net"])
        self.assertEqual(t2["sens"], "à venir")

    def test_le_sens_est_ecrit_en_mots(self):
        self.depense(avant_taxes="100")
        s = C.sommaire("2026-2027", date(2026, 11, 15), self.fichier)
        self.assertEqual(s["taxes"][0]["sens"], "remboursement à recevoir")
        self.assertLess(s["taxes"][0]["net"], 0)

        self.revenu(avant_taxes="1000")
        s = C.sommaire("2026-2027", date(2026, 11, 15), self.fichier)
        self.assertEqual(s["taxes"][0]["sens"], "remise à faire")

    def test_une_piece_ne_compte_que_dans_son_trimestre(self):
        self.revenu(date="2027-03-05", avant_taxes="200")
        s = C.sommaire("2026-2027", date(2027, 4, 1), self.fichier)
        self.assertEqual(s["taxes"][0]["tps_percue"], 0.0)
        self.assertEqual(s["taxes"][1]["tps_percue"], 10.0)


# ── 4. Renouvellement : rien ne se renouvelle tout seul ────────────────────
class TestRenouvellement(Base):

    def etat(self, jours, today=date(2026, 11, 15)):
        ligne = {"echeance": (today + timedelta(days=jours)).isoformat()}
        return C.etat_renouvellement(ligne, today)[0]

    def test_alerte_trente_jours_avant(self):
        self.assertEqual(self.etat(31), "en_cours")
        self.assertEqual(self.etat(30), "a_renouveler")   # la borne alerte
        self.assertEqual(self.etat(1),  "a_renouveler")
        self.assertEqual(self.etat(0),  "a_renouveler")   # le jour même
        self.assertEqual(self.etat(-1), "echu")

    def test_sans_echeance_aucune_alerte(self):
        code, libelle, jours = C.etat_renouvellement({"echeance": None},
                                                     date(2026, 11, 15))
        self.assertEqual(code, "aucune")
        self.assertIsNone(jours)
        self.assertIn("ponctuel", libelle)

    def test_le_renouvellement_est_manuel(self):
        annuel = self.revenu(echeance="2027-11-10")
        ponctuel = self.revenu(echeance="")
        self.assertEqual(annuel["renouvellement"], "manuel")
        self.assertEqual(ponctuel["renouvellement"], "aucun")

    def test_les_alertes_remontent_dans_le_sommaire(self):
        self.revenu(client="Proche", echeance="2026-12-10")      # dans 25 jours
        self.revenu(client="Loin",   echeance="2027-10-01")      # dans ~1 an
        self.revenu(client="Passe",  echeance="2026-11-10")      # échu
        s = C.sommaire("2026-2027", date(2026, 11, 15), self.fichier)
        noms = sorted(a["client"] for a in s["alertes"])
        self.assertEqual(noms, ["Passe", "Proche"])
        self.assertEqual(s["jours_alerte"], 30)

    def test_une_echeance_depassee_ne_disparait_pas(self):
        self.revenu(client="Passe", echeance="2026-11-01")
        s = C.sommaire("2026-2027", date(2026, 11, 15), self.fichier)
        self.assertEqual(len(s["revenus"]), 1)
        self.assertEqual(s["revenus"][0]["renouv_code"], "echu")


# ── 5. Le mur de compagnie et « à préciser » ───────────────────────────────
class TestMurEtClassement(Base):

    def test_la_ligne_a_preciser_existe_toujours(self):
        s = C.sommaire("2026-2027", date(2026, 11, 15), self.fichier)
        self.assertEqual(len(s["ventilation"]), 4)
        self.assertTrue(s["ventilation"][-1]["a_preciser"])

    def test_une_piece_sans_activite_tombe_a_preciser(self):
        ligne = C.ajouter_depense(
            {"date": "2026-11-12", "fournisseur": "Inconnu", "avant_taxes": "40"},
            self.fichier)
        self.assertEqual(ligne["activite"], C.A_PRECISER)

    def test_a_preciser_nest_jamais_fondu_dans_une_marque(self):
        C.ajouter_depense({"date": "2026-11-12", "fournisseur": "Inconnu",
                           "avant_taxes": "40"}, self.fichier)
        s = C.sommaire("2026-2027", date(2026, 11, 15), self.fichier)
        par_code = {v["code"]: v for v in s["ventilation"]}
        self.assertEqual(par_code["a_preciser"]["depenses"], 40.0)
        for code in C.ACTIVITES_CHOISISSABLES:
            self.assertEqual(par_code[code]["depenses"], 0.0)
        self.assertEqual(s["totaux"]["a_preciser"], 1)

    def test_classer_deplace_la_piece(self):
        ligne = C.ajouter_depense({"date": "2026-11-12", "fournisseur": "Inconnu",
                                   "avant_taxes": "40"}, self.fichier)
        maj = C.classer("depense", ligne["id"], "nano", self.fichier)
        self.assertEqual(maj["activite"], "nano")
        self.assertIn("classe_le", maj)
        s = C.sommaire("2026-2027", date(2026, 11, 15), self.fichier)
        par_code = {v["code"]: v for v in s["ventilation"]}
        self.assertEqual(par_code["nano"]["depenses"], 40.0)
        self.assertEqual(par_code["a_preciser"]["depenses"], 0.0)

    def test_classer_refuse_une_cible_invalide(self):
        ligne = self.revenu()
        with self.assertRaises(ValueError):
            C.classer("revenu", ligne["id"], "a_preciser", self.fichier)
        with self.assertRaises(ValueError):
            C.classer("revenu", ligne["id"], "solarium_pro", self.fichier)
        with self.assertRaises(ValueError):
            C.classer("autre", ligne["id"], "nano", self.fichier)
        with self.assertRaises(LookupError):
            C.classer("revenu", "REV-9999", "nano", self.fichier)

    def test_rien_de_solarium_pro_dans_le_module(self):
        """Le mur de compagnie commence dans le code : ce module ne nomme
        aucune source de Solarium Pro."""
        with open(os.path.join(os.path.dirname(ICI), "comptabilite.py"),
                  encoding="utf-8") as f:
            source = f.read().lower()
        for interdit in ("solariumdashboard", "solariumcomptable", "solariumfactures",
                         "budget_sp", "registre_factures", "solarium-factures"):
            self.assertNotIn(interdit, source)


# ── 6. Le fichier de données ───────────────────────────────────────────────
class TestFichier(Base):

    def test_enveloppe_jamais_une_liste_nue(self):
        self.revenu()
        with open(self.fichier, encoding="utf-8") as f:
            brut = json.load(f)
        self.assertIsInstance(brut, dict)
        self.assertEqual(brut["version"], 1)
        self.assertIn("maj_le", brut)
        self.assertIsInstance(brut["revenus"], list)

    def test_une_liste_nue_est_refusee(self):
        with open(self.fichier, "w", encoding="utf-8") as f:
            json.dump([{"date": "2026-11-10"}], f)
        with self.assertRaises(ValueError):
            C.charger(self.fichier)

    def test_le_chemin_nest_pas_fige_a_l_import(self):
        """Un `chemin=CONSTANTE` en défaut écrirait dans le vrai fichier
        malgré la suite — vérifié, pas supposé."""
        def lire_vrai():
            if not os.path.exists(C.FICHIER):
                return None
            with open(C.FICHIER, encoding="utf-8") as f:
                return f.read()
        avant = lire_vrai()
        self.revenu()
        self.assertEqual(lire_vrai(), avant)

    def test_identifiants_successifs(self):
        a, b = self.revenu(), self.revenu()
        self.assertEqual((a["id"], b["id"]), ("REV-0001", "REV-0002"))
        c = self.depense()
        self.assertEqual(c["id"], "DEP-0001")


# ── 7. Les routes ──────────────────────────────────────────────────────────
class TestRoutes(Base):

    def setUp(self):
        super().setUp()
        S.app.config["TESTING"] = True
        self.cli = S.app.test_client()

    def test_lecture(self):
        r = self.cli.get("/api/comptabilite")
        self.assertEqual(r.status_code, 200)
        d = r.get_json()["data"]
        self.assertEqual(d["compagnie"], "Prospect 2.0")
        self.assertEqual(d["exercices"], C.exercices_disponibles())

    def test_ajout_par_la_route(self):
        r = self.cli.post("/api/comptabilite/revenu", json={
            "date": "2026-11-12", "client": "Marchand", "avant_taxes": "150",
            "activite": "decopatio", "echeance": "2027-11-12"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["ok"])
        d = self.cli.get("/api/comptabilite").get_json()["data"]
        self.assertEqual(d["totaux"]["revenus"], 150.0)
        self.assertEqual(d["revenus"][0]["activite_libelle"], "Prospect 2.0 / DécoPatio")

    def test_route_refuse_le_retroactif(self):
        r = self.cli.post("/api/comptabilite/depense", json={
            "date": "2026-10-20", "fournisseur": "X", "avant_taxes": "10"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("rétroactif", r.get_json()["error"])

    def test_route_de_classement(self):
        self.cli.post("/api/comptabilite/depense", json={
            "date": "2026-11-12", "fournisseur": "Inconnu", "avant_taxes": "40"})
        r = self.cli.post("/api/comptabilite/activite", json={
            "type": "depense", "id": "DEP-0001", "activite": "general"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["libelle"], "Prospect 2.0 / Général")
        r = self.cli.post("/api/comptabilite/activite", json={
            "type": "depense", "id": "DEP-0404", "activite": "general"})
        self.assertEqual(r.status_code, 404)

    def test_export_csv_porte_les_libelles(self):
        self.cli.post("/api/comptabilite/revenu", json={
            "date": "2026-11-12", "client": "Marchand", "avant_taxes": "150",
            "activite": "nano"})
        r = self.cli.get("/api/comptabilite/export/csv")
        self.assertEqual(r.status_code, 200)
        texte = r.data.decode("utf-8")
        self.assertIn("Prospect 2.0 / Nano Protection", texte)
        self.assertIn("Prospect 2.0 / DécoPatio", texte)   # la ventilation entière
        self.assertNotIn("Solarium", texte)

    def test_export_pdf_porte_les_libelles(self):
        self.cli.post("/api/comptabilite/revenu", json={
            "date": "2026-11-12", "client": "Marchand", "avant_taxes": "150",
            "activite": "decopatio", "echeance": "2026-12-01"})
        r = self.cli.get("/api/comptabilite/export/pdf")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data.startswith(b"%PDF"))
        chemin = os.path.join(self.dossier, "rapport.pdf")
        with open(chemin, "wb") as f:
            f.write(r.data)
        import subprocess
        texte = subprocess.run(["pdftotext", chemin, "-"], capture_output=True,
                               text=True).stdout
        self.assertIn("Prospect 2.0 / DécoPatio", texte)
        self.assertIn("à renouveler", texte)
        # « Solarium Pro » n'apparaît que dans les deux phrases du mur de
        # compagnie — jamais dans une ligne de chiffres.
        for ligne in texte.splitlines():
            if "Solarium" in ligne:
                self.assertTrue("séparée de Solarium Pro" in ligne
                                or "Aucune donnée de Solarium Pro" in ligne,
                                "Solarium Pro apparaît ailleurs : %r" % ligne)


# ── 8. La page : l'onglet existe vraiment dans le HTML ─────────────────────
class TestPage(unittest.TestCase):

    def test_le_html_porte_l_onglet_et_les_libelles_viennent_du_serveur(self):
        with open(os.path.join(os.path.dirname(ICI), "dashboard_prospect2.html"),
                  encoding="utf-8") as f:
            page = f.read()
        self.assertIn('data-onglet="comptabilite"', page)
        self.assertIn('id="panneau-comptabilite"', page)
        # Le libellé n'est JAMAIS écrit en dur dans la page : il vient de
        # l'API. Sinon deux sources finiraient par diverger.
        self.assertNotIn("Prospect 2.0 / DécoPatio", page)
        self.assertIn("activite_libelle", page)
        # `hidden` doit gagner contre toute classe qui poserait un display.
        self.assertIn("[hidden] { display: none !important; }", page)


if __name__ == "__main__":
    unittest.main(verbosity=2)
