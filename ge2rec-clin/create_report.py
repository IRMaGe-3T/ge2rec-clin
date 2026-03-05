import os
import re
from nilearn import masking
from nilearn.plotting import plot_carpet

from report import ClinicalReportBuilder
from useful import plot_slice_planes, plot_realignment_parameters
from lateralization import get_lateralization_curves


def create_report(analysis_directory, subject_info, acq_info, fmri_files, anat_file):

    inputs = {
        "subject_info" :subject_info,
        "acq_info": acq_info
    }

    out_dir = os.path.join(analysis_directory, "reports")
    os.makedirs(out_dir, exist_ok=True)
    report_path = os.path.join(
        analysis_directory,
        f"sub-{subject_info["subject"]}_ses-{subject_info["session"]}_ge2rec-clin_report.pdf"
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
    # c0r fig
    norm_anat_fig_rows_cor = 3
    norm_anat_fig_cols_cor = 5
    norm_anat_inf_slice_start_cor = 17
    norm_anat_slices_gap_cor = 8

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
        if task in ["gene", "reco"]:
            num ="0002"
        spmT = os.path.join(
            os.path.dirname(func_run).replace("raw",f"stats_{task}"),
            f"spmT_{num}.nii"
        )
        
        realignment_parameters = os.path.join(
            os.path.dirname(func_run).replace("raw","spm_preprocessing"),
            "realign", "rp_" + func_name + ".txt"
        )
        tr =  acq_info[task]["tr"]
        voxel_size = acq_info[task]["voxel_size"]
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
            t_r=tr / 1000,
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
                fig_rows=norm_anat_fig_rows_sag,
                fig_cols=norm_anat_fig_cols_sag,
                slice_start=norm_anat_inf_slice_start_sag,
                slice_step=norm_anat_slices_gap_sag,
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
                fig_rows=norm_anat_fig_rows_cor,
                fig_cols=norm_anat_fig_cols_cor,
                slice_start=norm_anat_inf_slice_start_cor,
                slice_step=norm_anat_slices_gap_cor,
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
            out_png_images = get_lateralization_curves(spmT, analysis_directory)
            inputs["lateralization"] =  out_png_images

        elif task == "reco":
            title = "Mémoire reconnaissance - Carte Statistique"
            desc = "Activation cérébrales pour la tâche de mémoire (reconnaissance "\
                "des mots entendus à la tâche précédente à partir d'image):"
            #performance
        elif task == "rappel":
            title = "Mémoire rappel - Carte Statistique"
            desc =  "Activation cérébrales pour la tâche de rappel libre" \
                    "(reconnaissance des mots entendus lors de la première tâche "\
                    "à partir du son et générartion de la même phrase):"

        # QC 
        inputs[f"{task}_info"]=  {
            "image": fmri_ax,
            "carpet": carpet_img,
            "rot": out_file_rot,
            "tra": out_file_tra,
            "check": im_check
        }
        inputs[f"{task}_stats"]=  {
            "axial": stats_ax,
            "cor": stats_cor,
            "sag": stats_sag,
            "title": title,
            "desc": desc

        }

    builder = ClinicalReportBuilder(
        output_path=report_path,
        inputs=inputs
    )

    builder.build()