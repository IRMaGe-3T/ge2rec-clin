import os
import re
from nilearn import masking
from nilearn.plotting import plot_carpet

from report import ClinicalReportBuilder
from useful import plot_slice_planes, plot_realignment_parameters, plot_orthogonal_mosaics
from lateralization import get_lateralization_curves, ROIS_LATERALIZATION
from eprime import get_reco_result


def create_report(analysis_directory, subject_info, acq_info, fmri_files, anat_file, name, eprime_file=None):

    inputs = {
        "name": name,
        "subject_info" :subject_info,
        "acq_info": acq_info
    }

    out_dir = os.path.join(analysis_directory, "reports")
    os.makedirs(out_dir, exist_ok=True)
    report_path = os.path.join(
        analysis_directory,
        f"sub-{subject_info["subject"]}_ses-{subject_info["session"]}_{name}_report.pdf"
    )

    # Generate images and text for report 
    norm_func_cmap = "Greys_r"
    norm_anat_cmap = "Greys_r"
    spmT_cmap = "rainbow"
    # axial fig
    norm_anat_fig_rows = 5
    norm_anat_fig_cols = 5
    norm_anat_inf_slice_start = 29
    norm_anat_slices_gap = 5
    norm_anat_qc_fig_rows = 3
    norm_anat_qc_fig_cols = 5
    norm_anat_qc_inf_slice_start = 40
    norm_anat_qc_slices_gap = 5
    func_fig_rows = 6
    func_fig_cols = 5
    func_inf_slice_start = 7
    func_slices_gap = 1
    # sag fig
    norm_anat_fig_rows_sag = 3
    norm_anat_fig_cols_sag = 5
    norm_anat_inf_slice_start_sag =17
    norm_anat_slices_gap_sag = 8
    func_fig_rows_sag = 7
    func_fig_cols_sag = 5
    func_inf_slice_start_sag =8
    func_slices_gap_sag = 4
    # c0r fig
    func_fig_rows_cor = 6
    func_fig_cols_cor = 5
    func_inf_slice_start_cor = 13
    func_slices_gap_cor = 5

    # spmT min-max 
    spmT_vmin = 2.5
    spmT_vmax = 5

    # Anat
    anat_name = os.path.basename(anat_file).split('.')[0]
    norm_anat = os.path.join(
        os.path.dirname(anat_file).replace("raw", "spm_preprocessing"),
        "normalize_anat", "wm" + anat_name + ".nii"
    )
    anat_ax = plot_slice_planes(
        data_1=norm_anat,
        fig_rows=norm_anat_qc_fig_rows,
        fig_cols=norm_anat_qc_fig_cols,
        slice_start=norm_anat_qc_inf_slice_start,
        slice_step=norm_anat_qc_slices_gap,
        cmap_1=norm_anat_cmap,
        out_dir=out_dir,
        convention="radiological"
    )
    anat_sag = plot_slice_planes(
        data_1=norm_anat,
        plane="sag",
        fig_rows=norm_anat_fig_rows_sag,
        fig_cols=norm_anat_fig_cols_sag,
        slice_start=norm_anat_inf_slice_start_sag,
        slice_step=norm_anat_slices_gap_sag,
        cmap_1=norm_anat_cmap,
        cmap_2=spmT_cmap,
        out_dir=out_dir,
        convention="radiological"
    )
    inputs["t1_qc"] = {
        "axial": anat_ax,
        "sag": anat_sag
    }

    for func_run in fmri_files:
        task = re.search(r"task-([^_]+)", func_run).group(1)
        out_dir_task = os.path.join(out_dir, task)
        os.makedirs(out_dir_task, exist_ok=True)

        
        func_name = os.path.basename(func_run).split('.')[0]
        num = "0001"
        if task in ["reco"]:
             num ="0002"
        name_task = task
        if "run" in func_name:
            nb = re.search(r"run-([^_]+)",func_name).group(1)
            name_task += f"_run-{nb}"
        spmT = os.path.join(
            os.path.dirname(func_run).replace("raw",f"stats_{name_task}"),
            f"spmT_{num}.nii"
        )
        
        realignment_parameters = os.path.join(
            os.path.dirname(func_run).replace("raw","spm_preprocessing"),
            "realign", "rp_" + func_name + ".txt"
        )
        tr =  acq_info[name_task]["tr"]
        voxel_size = acq_info[name_task]["voxel_size"]
        # Raw fmri
        fmri_ax = plot_slice_planes(
            data_1=func_run,
            fig_rows=func_fig_rows,
            fig_cols=func_fig_cols,
            slice_start=func_inf_slice_start,
            slice_step=func_slices_gap,
            cmap_1=norm_func_cmap,
            out_dir=out_dir_task,
            convention="radiological"
        )
        # carpet plot
        func_mask = masking.compute_epi_mask(func_run)
        carpet = plot_carpet(
            func_run,
            func_mask,
            t_r=tr,
            standardize="zscore_sample",
            title="global patterns over time",
        )
        carpet_img = os.path.join(
            out_dir_task,
            f"{func_name}_carpet.png",
        )
        carpet.savefig(carpet_img, format="png", dpi=200)
        # Realignment
        sources_images_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "sources_images"
        )
        out_file_tra = os.path.join(
            out_dir_task,
            f"{func_name}_QC_translation.png",
        )
        out_file_rot = os.path.join(
           out_dir_task,
            f"{func_name}_QC_rotation.png",
        )
        qc = plot_realignment_parameters(
            realignment_parameters,
            voxel_size,
            out_file_tra,
            out_file_rot,
        )

        if qc is False:
            im_check = os.path.join(sources_images_dir, "No-check-mark.png")
        elif qc is True:
            im_check =  os.path.join(sources_images_dir, "OK-check-mark.png")
        
        stats_ax= plot_slice_planes(
                data_1=norm_anat,
                data_2=spmT,
                fig_rows=norm_anat_fig_rows,
                fig_cols=norm_anat_fig_cols,
                slice_start=norm_anat_inf_slice_start,
                slice_step=norm_anat_slices_gap,
                cmap_1=norm_anat_cmap,
                cmap_2=spmT_cmap,
                vmin_2=spmT_vmin,
                vmax_2=spmT_vmax,
                out_dir=out_dir_task,
                convention="radiological"
            )           
        stats_sag = plot_slice_planes(
                data_1=norm_anat,
                data_2=spmT,
                plane="sag",
                fig_rows=func_fig_rows_sag,
                fig_cols=func_fig_cols_sag,
                slice_start=func_inf_slice_start_sag,
                slice_step=func_slices_gap_sag,
                cmap_1=norm_anat_cmap,
                cmap_2=spmT_cmap,
                vmin_2=spmT_vmin,
                vmax_2=spmT_vmax,
                out_dir=out_dir_task,
                convention="radiological"
            )
        
        stats_cor = plot_slice_planes(
                data_1=norm_anat,
                data_2=spmT,
                plane="cor",
                fig_rows=func_fig_rows_cor,
                fig_cols=func_fig_cols_cor,
                slice_start=func_inf_slice_start_cor,
                slice_step=func_slices_gap_cor,
                cmap_1=norm_anat_cmap,
                cmap_2=spmT_cmap,
                vmin_2=spmT_vmin,
                vmax_2=spmT_vmax,
                out_dir=out_dir_task,
                convention="radiological"
            )
        
        if task == "gene":
            title = "Production langage - Carte Statistique"
            desc = "Activation cérébrales pour la tâche de génération de phrases "\
                "à partir de mots entendus:"
            # Lateralization
            inputs["lateralization"] =  get_lateralization_curves(spmT, analysis_directory)
            activation = "activation"
            # snapshot atlas lateralization
            # Altas snapshot
            atlas_snap = {}
            for roi in ROIS_LATERALIZATION:
                atlas_snap[roi] = plot_orthogonal_mosaics(
                    data_1=norm_anat,
                    data_2=ROIS_LATERALIZATION[roi]["path"],
                    slices=ROIS_LATERALIZATION[roi]["slices"],
                    cmap_1=norm_anat_cmap,
                    color_2="blue",
                    alpha=0.6,
                    out_dir=out_dir_task,
                    out_name=f"mosaics_atlas_{roi}",
                    dpi=200,
                )
            inputs["atlas_snap"] = atlas_snap
        elif task == "reco":
            title = "Mémoire reconnaissance - Carte Statistique"
            desc = "Activation cérébrales pour la tâche de mémoire (reconnaissance "\
                "des mots entendus à la tâche précédente à partir d'image):"
            activation = "reconnaisance"
            #performance
        elif task == "rappel":
            title = "Mémoire rappel - Carte Statistique"
            desc =  "Activation cérébrales pour la tâche de rappel libre" \
                    "(reconnaissance des mots entendus lors de la première tâche "\
                    "à partir du son et générartion de la même phrase):"
            activation = "rappel"
        elif task == "langAud":
            title = "IRMf de langage (stimulation auditive)- Carte Statistique"
            desc = "Activation cérébrale pour la tâche de langage (stimulation auditive)"
            activation = "langage"
        elif task == "langVis":
            title = "IRMf de langage (stimulation visuelle) - Carte Statistique"
            desc = "Activation cérébrale pour la tâche de langage (stimulation visuelle)"
            activation = "langage"
        elif task == "lang":
            title = "IRMf de langage - Carte Statistique"
            desc = "Activation cérébrale pour la tâche de langage"
            activation = "langage"
        elif task == "mainD":
            title = "IRMf moteur (main droite) - Carte Statistique"
            desc = "Activation cérébrale pour la tâche motrice"
            activation = "moteur"
        elif task == "mainG":
            title = "IRMf moteur (main gauche) - Carte Statistique"
            desc = "Activation cérébrale pour la tâche motrice"
            activation = "moteur"
        elif task == "piedD":
            title = "IRMf moteur (pied droit) - Carte Statistique"
            desc = "Activation cérébrale pour la tâche motrice"
            activation = "moteur"
        elif task == "piedG":
            title = "IRMf moteur (pied gauche) - Carte Statistique"
            desc = "Activation cérébrale pour la tâche motrice"
            activation = "moteur"
        elif task == "lèvre":
            title = "IRMf moteur (levres) - Carte Statistique"
            desc = "Activation cérébrale pour la tâche motrice"
            activation = "moteur"
        elif task == "handmotor":
            title = "IRMf moteur (main bilatérale) - Carte Statistique"
            desc = "Activation cérébrale pour la tâche motrice"
            activation = "moteur"
        elif task == "clin":
            if "run" in func_name:
                nb = re.search(r"run-([^_]+)",func_name).group(1)
            title = f"IRMf de langage ou moteur - Carte Statistique ({nb})"
            desc = "Activation cérébrale pour une tâche motrice (main, pied ou lèvres) ou pour une tâche de langage"
            activation = "clinique"

        # QC 
        inputs[f"{name_task}_info"]=  {
            "name": name_task,
            "activation": activation, 
            "image": fmri_ax,
            "carpet": carpet_img,
            "rot": out_file_rot,
            "tra": out_file_tra,
            "check": im_check
        }
        inputs[f"{name_task}_stats"]=  {
            "axial": stats_ax,
            "cor": stats_cor,
            "sag": stats_sag,
            "title": title,
            "desc": desc

        }
    if eprime_file:
        csv_file = os.path.join(analysis_directory, "eprime_reco_result.csv")
        get_reco_result(eprime_file, csv_file)
        inputs["reco_result"] = csv_file

    builder = ClinicalReportBuilder(
        output_path=report_path,
        inputs=inputs
    )

    builder.build()