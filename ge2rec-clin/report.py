import pandas as pd

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, HRFlowable
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from datetime import datetime


class ClinicalReportBuilder:
    def __init__(self, output_path, inputs):
        self.output_path = output_path
        self.inputs = inputs 
        self.doc = SimpleDocTemplate(self.output_path, pagesize=A4,
                                     rightMargin=40, leftMargin=40,
                                     topMargin=80, bottomMargin=50)
        self.styles = getSampleStyleSheet()
        self.styles.add(ParagraphStyle(name="Center", alignment=TA_CENTER))
        self.styles.add(ParagraphStyle(name="Justify", alignment=TA_JUSTIFY))
        self.styles.add(
            ParagraphStyle(
                name="Bullet1",
                leftIndent=30,
                bulletOffsetY=2,
                bulletIndent=20,
                bulletFontSize=6,
                bulletColor="black",
                bulletText="●",
            )
        )
        self.elements = []

    def _header_footer(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.drawString(40, 820, f"{self.inputs.get(f"name")}_rapport")
        canvas.drawRightString(550, 820, f"{doc.page}")
        canvas.restoreState()

    # -------------------- Pages --------------------
    def page_cover(self, tittle):

        def trad(value):
            if value == "Yes":
                new_value = "Oui"
            elif value == "No":
                new_value = "Non"
            elif value == "Unknown":
                new_value = "Non renseigné"
            elif value == "Other":
                new_value = "Autre"
            elif value == "Left":
                new_value = "Gauche"
            elif value == "Right":
                new_value = "Droit"
            elif value == "Ambidextrous":
                new_value = "Ambidextre"
            elif value == "Bilateral":
                new_value = "Bilatéral"
            elif value == "Female":
                new_value = "Femme" 
            elif value == "Male":
                new_value = "Homme"
            else:
                new_value = value

            return new_value 
        
        today_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.elements.append(Paragraph(f"<font size=50><b>IRM fonctionnelle</b></font>", self.styles["Title"]))
        self.elements.append(Spacer(0 * mm, 15 * mm))
        self.elements.append(Paragraph(f"<font size=30><b>{tittle}</b></font>", self.styles["Title"]))
        self.elements.append(Spacer(0 * mm, 15* mm))
        self.elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        self.elements.append(Spacer(0 * mm, 12 * mm))
        subj = self.inputs.get("subject_info", {})
        acq = self.inputs.get("acq_info", {})
        self.elements.append(Paragraph(f"<font size=15><b>Patient {subj.get("subject")} (session : {subj.get("session")})</b></font>", self.styles["Center"]))
        self.elements.append(Spacer(0 * mm, 5 * mm))
        self.elements.append(HRFlowable(width="50%", thickness=1, color=colors.grey))
        self.elements.append(Spacer(0 * mm, 5 * mm))
        self.elements.append(Paragraph(f"<b>Date du rapport:</b> {today_date}", self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 5 * mm))
        self.elements.append(Paragraph(f"<u><b>Informations patients</b></u>", self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 2 * mm))
        self.elements.append(Paragraph(f"<b>Age du patient:</b> {subj.get("age")}", self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 1 * mm))
        self.elements.append(Paragraph(f"<b>Sexe du patient:</b> {trad(subj.get("sex"))}", self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 1 * mm))
        self.elements.append(Paragraph(f"<b>Main dominante:</b> {trad(subj.get("dominant_hand"))}", self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 1 * mm))
        self.elements.append(Paragraph(f"<b>Pathologie:</b> {trad(subj.get("pathology"))}", self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 1 * mm))
        self.elements.append(Paragraph(f"<b>Latéralisation de la pathologie:</b> {trad(subj.get("lateralization_pathology"))}", self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 1 * mm))
        self.elements.append(Paragraph(f"<b>Localisation de la pathologie:</b> {trad(subj.get("localization_pathology"))}", self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 1 * mm))
        self.elements.append(Paragraph(f"<b>Sclérose hippocampique ?</b> {trad(subj.get("hippo_sclerosis"))}", self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 1 * mm))
        self.elements.append(Paragraph(f"<b>Chirugie du cerveau ?</b> {trad(subj.get("brain_surgery"))}", self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 1 * mm))
        self.elements.append(Paragraph(f"<b>Bilan neuropsy?</b> {trad(subj.get("neuropsych_assessment"))}", self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 1 * mm))
        self.elements.append(Paragraph(f"<b>Bilan psychiatrique?</b> {trad(subj.get("psychiatric_assessment"))}", self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 5 * mm))
        self.elements.append(Paragraph(f"<u><b>Informations IRM</b></u>", self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 2 * mm))
        self.elements.append(Paragraph(f"<b>Site:</b> {acq["general"]["site"]}", self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 1 * mm))
        self.elements.append(Paragraph(f"<b>Machine IRM:</b> {acq["general"]["mri"]}", self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 1 * mm))
        self.elements.append(Paragraph(f"<b>Version logicielle IRM:</b> {acq["general"]["soft"]}", self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 60 * mm))
        self.elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        self.elements.append(Spacer(0 * mm, 5 * mm))
        self.elements.append(Paragraph("<b>DECHARGE DE RESPONSABILITE:</b>", self.styles["Normal"]))
        self.elements.append(Paragraph("Les résultats dans ce rapport sont obtenus dans un environnement de recherche.", self.styles["Normal"]))
        self.elements.append(PageBreak())

    def page_stats(self, task):
        stats = self.inputs.get(f"{task}_stats")
        if not stats:
            return
        self.elements.append(Paragraph(f"<font size=16 > <b> {stats["title"]} </b> </font>", self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 3 * mm))
        self.elements.append(Paragraph(stats["desc"], self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 2 * mm))
        im = Image(stats["axial"])
        im._restrictSize(180 * mm, 200 * mm)
        self.elements.append(im)
        self.elements.append(PageBreak())
        self.elements.append(Paragraph(f"<font size=16 > <b> {stats["title"]} </b> </font>", self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 3 * mm))
        self.elements.append(Paragraph(stats["desc"], self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 2 * mm))
        im = Image(stats["cor"])
        im._restrictSize(180 * mm, 200 * mm)
        self.elements.append(im)
        self.elements.append(PageBreak())
        self.elements.append(Paragraph(f"<font size=16 > <b> {stats["title"]} </b> </font>", self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 3 * mm))
        self.elements.append(Paragraph(stats["desc"], self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 2 * mm))
        im = Image(stats["sag"])
        im._restrictSize(180 * mm, 200 * mm)
        self.elements.append(im)
        self.elements.append(PageBreak())


    def page_lateralization(self):
        png_images_dic = self.inputs.get("lateralization", [])
        atlas_snap = self.inputs.get("atlas_snap", [])
        if not png_images_dic:
            return
        self.elements.append(Paragraph("<font size=16 > <b> Production langage - Evaluation quantitative </b> </font>", self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 3 * mm))
        desc = "Représentation de la latéralisation de la "\
        "production du langage. Les courbes noires montrent l'évolution de "\
        "l'index de latéralité en fonction du seuil statistique."
        self.elements.append(Paragraph(desc, self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 1 * mm))
        desc = "<b>N.B: </b> <i>Plus le seuil est élevé moins il "\
        "existe de faux positifs. Il est fortement conseillé de "\
        "prendre en compte un seuil supérieur à 3. </i>"
        self.elements.append(Paragraph(desc, self.styles["Normal"]))
        
        desc = {
            "temporal": "Temporal part",
            "frontal": "Frontal part",
            "middle_frontal_gyrus": "Atlas Harvard Oxford - Middle Frontal Gyrus",
            "inferior_frontal_gyrus_triangularis": "Atlas Harvard Oxford - Inferior Frontal Gyrus, pars triangularis",
            "inferior_frontal_gyrus_opercularis": "Atlas Harvard Oxford - Inferior Frontal Gyrus, pars opercularis",
            "superior_temporal_gyrus_anterior": "Atlas Harvard Oxford - Superior Temporal Gyrus, anterior division",
            "superior_temporal_gyrus_posterior": "Atlas Harvard Oxford - Superior Temporal Gyrus, posterior division",
            "middle_temporal_gyrus_temporooccipital": "Atlas Harvard Oxford - Middle Temporal Gyrus, temporooccipital part",
            "inferior_temporal_gyrus_anterior": "Atlas Harvard Oxford - Inferior Temporal Gyrus, anterior division",
            "inferior_tempotal_gyrus_posterior": "Atlas Harvard Oxford - Inferior Temporal Gyrus, posterior division"
        }
        i = 0
        for roi in list(png_images_dic.keys()):
            i += 1
            self.elements.append(Spacer(0 * mm, 8 * mm))
            message = Paragraph(
                f"<b>{desc[roi]}</b>",
                self.styles["Normal"]
            )
            image_atlas = Image(atlas_snap[roi])
            image_atlas._restrictSize(85 * mm, 30 * mm)
            image_atlas.hAlign = "CENTER"
            im = Image(png_images_dic[roi])
            im._restrictSize(130 * mm, 50 * mm)
            im.hAlign = "CENTER"
            table = [
                [message, image_atlas],
                [im, ""]
            ]

            t = Table(
                table,
                colWidths=[45 * mm, 85 * mm],
                rowHeights=[30 * mm, 50 * mm]
            )

            t.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("SPAN", (0, 1), (1, 1)),
                ("ALIGN", (1, 0), (1, 0), "CENTER"),
                ("ALIGN", (0, 1), (0, 1), "CENTER"),
            ]))

            t.hAlign = "CENTER"
            self.elements.append(t)
            self.elements.append(Spacer(0 * mm, 10 * mm))

            if i % 2 == 0 and i != len(png_images_dic):
                self.elements.append(PageBreak())
            
        desc = "<i><b>Réference</b>: LI toolbox - Wilke, Marko, and Karen Lidzba. "\
        "'LI-Tool: A New Toolbox to Assess Lateralization in Functional MR-Data.' Journal of Neuroscience Methods "\
        "163, no. 1 (June 15, 2007): 128–36. https://doi.org/10.1016/j.jneumeth.2007.01.026."\
        "Veuillez noter que ce logiciel n'a pas de marquage CE ou FDA.</i>"
        self.elements.append(Paragraph(desc, self.styles["Normal"]))
        self.elements.append(PageBreak())

    def page_task_performance(self):
        perf = self.inputs.get("reco_result")
        if not perf:
            return
        self.elements.append(Paragraph("<font size=16 > <b>  Mémoire reconnaissance - Performance </b> </font>", self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 10 * mm))
        desc = "<font size=10 > Performances comportementales"\
        "(mesurées pendant la tâche de reconnaissance des mots entendus à la tâche précédente à partir d'image) </font>"
        self.elements.append(Paragraph(desc, self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 10 * mm))

        m2 = Paragraph("<font size=10 ><b>% Bonnes réponses</b></font>")
        m3 = Paragraph("<font size=10 ><b>% Erreurs</b></font>")
        m4 = Paragraph("<font size=10 ><b>Anciens mots</b></font>")
        m5 = Paragraph("<font size=10 ><b>Nouveaux mots</b></font>")

        df = pd.read_csv(perf)
        new_correct = df.loc[df["CONDITION"] == "NEW", "Percent_correct"].iloc[0]
        new_error = df.loc[df["CONDITION"] == "NEW", "Percent_error"].iloc[0]

        old_correct = df.loc[df["CONDITION"] == "OLD", "Percent_correct"].iloc[0]
        old_error = df.loc[df["CONDITION"] == "OLD", "Percent_error"].iloc[0]

        behavioural_data = [
            ["", m2, m3],
            [m4, old_correct, old_error],
            [m5, new_correct, new_error],
        ]
        t = Table(behavioural_data)
        t.hAlign = "LEFT"
        self.elements.append(t)
        self.elements.append(PageBreak())


    def page_tasks_description_ge2rec(self):
        self.elements.append(Paragraph("Protocole GE2REC - Informations", self.styles["Title"]))
        self.elements.append(Spacer(0 * mm, 5 * mm))

        self.elements.append(
            Paragraph(
                "<font size=12 > Le protocole GE2REC est composé de trois "\
                "tâches interdépendantes : la génération de phrases avec "\
                "encodage implicite (GE) et deux tâches de mémoire "\
                "de rappel (2REC) qui sont la reconnaissance (RECO) "\
                "et le rappel (RE)<br/> </font>",
                self.styles["Justify"],
            )
        )
        self.elements.append(Spacer(0 * mm, 4 * mm))
        self.elements.append(
            Paragraph(
                "<font size=12 > Ce protocole permet de cartographier "\
                "l’interaction des fonctions du langage et de la mémoire "\
                "(LMN language memory network) au niveau individuel."\
                "Il fournit une évaluation exhaustive en incluant "\
                "des modalités verbales, visuelles et divers processus "\
                "langagiers et mémoriels. </font>",
                self.styles["Justify"],
            )
        )
        self.elements.append(Spacer(0 * mm, 4 * mm))
        self.elements.append(
            Paragraph(
                "<font size=12 > <b> Première tâche – Stimuli et tâche "\
                "de génération de phrases avec encodage implicite "\
                "(GE)</b><br/>"\
                "Il s'agit d'une séquence en bloc de génération de "\
                "phrases avec encodage implicite (durée de 7,3 minutes)."\
                "Les sujets écoutent des mots à travers un casque et doivent "\
                "générer des phrases de manière implicite. Lors des périodes "\
                "de contrôle, des pseudo-mots sont diffusés au sujet afin "\
                "qu’il n’y ait pas de génération. "\
                "Une croix de fixation apparaît lors des périodes de repos."\
                "</font> ",\
                self.styles["Justify"]
            )
        )

        self.elements.append(Spacer(0 * mm, 4 * mm))
        self.elements.append(
            Paragraph(
                "<font size=12 > <b> Deuxième tâche – Reconnaissance (RECO)"\
                "</b><br/>"\
                "La deuxième tâche est un paradigme évènementiel "\
                "(durée de 6,8min). "\
                "Des images sont présentées aux sujets selon un mode "\
                "pseudo-aléatoire de 2,5 secondes. "\
                "Ils doivent alors indiquer s’ils reconnaissent les images "\
                "des objets dont les noms ont été diffusés lors de "\
                "la première tâche GE. Dans le cadre clinique,"\
                "le choix proposé est binaire. "\
                "Soit le sujet indique qu’il reconnaît l’image (OLD), "\
                "soit qu’il s’agit d’un nouvel item (NEW).</font> ",
                self.styles["Normal"],
            )
        )

        self.elements.append(Spacer(0 * mm, 4 * mm))
        self.elements.append(
            Paragraph(
                "<font size=12 > <b> Troisième tâche – Rappel (RA)</b><br/>" \
                "La troisième tâche est un paradigme en bloc en modalité "\
                "auditive (durée de 4,17 minutes). Les participants "\
                "entendent les mots de la tâche GE et doivent se souvenir "\
                "de manière explicite des phrases précédemment "\
                "générées lors de la première tâche.</font> ",
                self.styles["Normal"],
            )
        )
        self.elements.append(PageBreak())


    def page_tasks_description_clin(self):
        self.elements.append(Paragraph("Protocole IRM fonctionnelle clinique - Informations", self.styles["Title"]))
        self.elements.append(Spacer(0 * mm, 5 * mm))

        self.elements.append(Spacer(0 * mm, 4 * mm))
        self.elements.append(
            Paragraph(
                "<font size=12 > <b> Langage – "\
                "Génération de phrases </b><br/>"\
                "Il s'agit d'une séquence en bloc de génération de "\
                "phrases avec encodage implicite."\
                "Les sujets écoutent des mots à travers un casque (ou en cas de problème auditif voient des mots affichés à l'écran) et doivent "\
                "générer des phrases."\
                "</font> ",\
                self.styles["Justify"]
            )
        )

        self.elements.append(Spacer(0 * mm, 4 * mm))
        self.elements.append(
            Paragraph(
                "<font size=12 > <b> Moteur"\
                "</b><br/>"\
                "Séquence en bloc avec mouvements soit du pied ou de la man (gauche ou droit) ou mouvement des lèvres. "\
                "</font> ",
                self.styles["Normal"],
            )
        )
        
        self.elements.append(PageBreak())


    def page_t1_info(self):
        qc = self.inputs.get(f"t1_qc")
        if not qc:
            return
        self.elements.append(Paragraph("<font size=16 > <b>IRM anatomique - Contrôle qualité</b> </font>", self.styles["Normal"]))
        info = self.inputs["acq_info"]
        self.elements.append(Spacer(0 * mm, 3 * mm))
        self.elements.append(Paragraph("<b>Paramètres d'acquisition: </b>", self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 1 * mm))
        self.elements.append(Paragraph(f"Procotocole d'acquisition / nom de séquence: {info["anat"]["description"]} / {info["anat"]["pulse_seq_name"]}", self.styles["Bullet1"]))
        self.elements.append(Spacer(0 * mm, 1 * mm))
        self.elements.append(Paragraph(f"Epaisseur de coupe [mm]: {info["anat"]["slice_thickness"]}", self.styles["Bullet1"]))
        self.elements.append(Spacer(0 * mm, 1 * mm))
        voxel = info["anat"]["voxel_size"]
        self.elements.append(Paragraph(f"Taille des voxels [mm]: {[round(voxel[0]), round(voxel[1]), round(voxel[2])]}", self.styles["Bullet1"]))
        self.elements.append(Spacer(0 * mm, 1 * mm))
        self.elements.append(Paragraph(f"TR [ms] / TE [ms] / flip angle: {info["anat"]["tr"]*1000} / {info["anat"]["te"]*1000} / {info["anat"]["fa"]}", self.styles["Bullet1"]))
        self.elements.append(Spacer(0 * mm, 1 * mm))
        self.elements.append(Image(qc["axial"],width=177 * mm, height=127 * mm))
        self.elements.append(Spacer(0 * mm, 2 * mm))
        self.elements.append(Image(qc["sag"],width=177 * mm, height=80 * mm))
        self.elements.append(PageBreak())

    def pages_irmf_info(self, task):
        qc = self.inputs.get(f"{task}_info")
        if not qc:
            return
        info = self.inputs["acq_info"]        
        self.elements.append(Paragraph(f"<font size=16 > <b>IRM fonctionnelle {task} ({qc["activation"]}) - Contrôle qualité </b> </font>", self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 3 * mm))
        self.elements.append(Paragraph("<b>Paramètres d'acquisition: </b>:", self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 1 * mm))
        self.elements.append(Paragraph(f"Procotocole d'acquisition / nom de séquence: {info[task]["description"]} / {info[task]["pulse_seq_name"]}", self.styles["Bullet1"]))
        self.elements.append(Spacer(0 * mm, 1 * mm))
        self.elements.append(Paragraph(f"Epaisseur de coupe [mm]: {info[task]["slice_thickness"]}", self.styles["Bullet1"]))
        self.elements.append(Spacer(0 * mm, 1 * mm))
        voxel = info[task]["voxel_size"]
        self.elements.append(Paragraph(f"Taille des voxels [mm]: {[round(voxel[0]), round(voxel[1]), round(voxel[2])]}", self.styles["Bullet1"]))
        self.elements.append(Spacer(0 * mm, 1 * mm))
        self.elements.append(Paragraph(f"TR [ms] / TE [ms] / flip angle: {float(info[task]["tr"]*1000)} / {float(info[task]["te"]*1000)} / {info[task]["fa"]}", self.styles["Bullet1"]))
        self.elements.append(Spacer(0 * mm, 1 * mm))
        self.elements.append(Image(qc["image"],width=177 * mm, height=182 * mm))
        self.elements.append(PageBreak())

        self.elements.append(Paragraph(f"<font size=16 > <b>IRMf tâche de {task} - Contrôle qualité </b> </font>", self.styles["Normal"]))
        self.elements.append(Spacer(0 * mm, 2 * mm))
        self.elements.append(Paragraph("<b>Intensité des voxels au cours du temps: </b>:", self.styles["Normal"]))
        self.elements.append(Image(qc["carpet"], width=152 * mm, height=70*mm))
        self.elements.append(Spacer(0 * mm, 1 * mm))
        im_check = (Image(qc["check"],  width=13 * mm, height=12.4*mm))
        message = Paragraph(
            "<font size=10 > <b> Mouvements: </b> </font>",
            self.styles["Normal"],
        )
        im_check.hAlign = "CENTER"
        title = [[message, im_check]]
        t = Table(title, [110 * mm, 30 * mm])  # colWidths, rowHeight
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        t.hAlign = "LEFT"
        self.elements.append(t)
        self.elements.append(Spacer(0 * mm, 1 * mm))
        self.elements.append(Image(qc["rot"],  width=152 * mm, height=70*mm))
        self.elements.append(Spacer(0 * mm, 1 * mm))
        self.elements.append(Image(qc["tra"],  width=152 * mm, height=70*mm))
        self.elements.append(PageBreak())

    def build(self):
        list_task = [v['name'] for v in self.inputs.values() if 'name' in v]
        task_order = ["gene", "reco", "rappel", "langVis", "langAud", "clin", "handmotor"]
        list_task.sort(key=lambda x: task_order.index(x) if x in task_order else len(task_order))
        ge2rec = False
        clinic = False
        tittle = ""
        if "reco" in list_task:
            ge2rec = True
            tittle += "GE2REC (langage et mémoire)"
        if any("clin" in x for x in list_task) or any("lang" in x for x in list_task) or any("mot" in x for x in list_task):
            clinic = True
            tittle += "clinique (langage et/ou moteur)"

        self.page_cover(tittle)
        for task in list_task:
            if "reco" in task:
                self.page_task_performance()
            self.page_stats(task)
            if "gene" in task:
                self.page_lateralization()  
        if ge2rec:
            self.page_tasks_description_ge2rec()
        if clinic:
            self.page_tasks_description_clin()
        self.page_t1_info()
        for task in list_task:
            self.pages_irmf_info(task)
        # Create PDF
        self.doc.build(self.elements, onFirstPage=self._header_footer, onLaterPages=self._header_footer)



