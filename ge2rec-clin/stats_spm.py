import os
import logging
import pandas as pd
import re
from nipype import Node, Workflow
from nipype.interfaces.io import DataSink
from nipype.interfaces.spm import (
    Level1Design,
    EstimateModel,
    EstimateContrast
)
from nipype.interfaces.utility import IdentityInterface


from useful import archive_spm_scripts


logger = logging.getLogger(__name__)


def build_session_info_single_run(
    task_name,
    scan,
    events_tsv,
    motion_file,
    hpf=128,
    tmod=0,
    orth=1
):
    """
    Build session_info structure for ONE functional run (SPM/Nipype).

    Parameters
    ----------
    events_tsv : str
        Path to BIDS events.tsv file
    motion_file : str
        Path to SPM realignment file (rp_*.txt)
    hpf : int
        High-pass filter (default 128)
    tmod : int
        Time modulation (default 0)
    orth : int
        Orthogonalization flag (1 or 0)

    Returns
    -------
    session_info : list
        List containing one session dictionary (SPM format)
    """

    task_order = {
        "gene": ["GENE", "CONTROL"],
        "reco":  ["OLD", "CONTROL", "NEW"],
        "rappel":  ["RAPPEL"],
        "langVis": ["LANGAGE"],
        "langAud": ["LANGAGE"],
        "clin": ["CLIN"],
        "handmotor": ["MOTOR", "REST"]
    }

    if not os.path.exists(events_tsv):
        raise FileNotFoundError(f"events file not found: {events_tsv}")

    if not os.path.exists(motion_file):
        raise FileNotFoundError(f"motion file not found: {motion_file}")

    df = pd.read_csv(events_tsv, sep="\t")

    if "trial_type" not in df.columns:
        raise ValueError("events.tsv must contain a 'trial_type' column")

    if "onset" not in df.columns:
        raise ValueError("events.tsv must contain an 'onset' column")

    if "duration" not in df.columns:
        raise ValueError("events.tsv must contain a 'duration' column")

    # Identify unique conditions
    conditions = sorted(df["trial_type"].unique())

    cond_list = []

    ordered_conditions = task_order.get(task_name, conditions)

    for cond in ordered_conditions:
        sub_df = df[df["trial_type"] == cond]

        cond_dict = {
            "name": cond,
            "onset": sub_df["onset"].tolist(),
            "duration": sub_df["duration"].tolist(),
            "tmod": tmod,
            "pmod": None,
            "orth": orth
        }

        cond_list.append(cond_dict)
    

    session_dict = {
        "scans": scan,
        "cond": cond_list,
        "multi_reg": [{motion_file}],
        "hpf": hpf
    }

    return [session_dict]


# -------------------------------------------------------------------------
# Build contrasts
# -------------------------------------------------------------------------
def build_contrasts(contrast_definitions):
    """
    Build contrast list for EstimateContrast.

    contrast_definitions format:
    [
        {
            "name": "CondA > CondB",
            "type": "T",
            "conditions": ["CondA", "CondB"],
            "weights": [1, -1]
        }
    ]
    """

    contrasts = []

    for c in contrast_definitions:
        contrasts.append(
            (c["name"],
             c["type"],
             c["conditions"],
             c["weights"])
        )

    return contrasts


# -------------------------------------------------------------------------
# Create Level1 workflow
# -------------------------------------------------------------------------
def create_stats_workflow(
    name,
    output_dir,
    working_dir,
    func_runs,
    tr,
    session_info,
    contrasts
):
    """
    Create stats (level1, estimate model and estimate contrast) SPM workflow.
    """

    wf = Workflow(name=f"spm_stats_{name}")
    wf.base_dir = working_dir

    # ---------------------------------------------------------------------
    # Input node
    # ---------------------------------------------------------------------
    inputnode = Node(
        IdentityInterface(fields=["func_runs", "realignement_params"]),
        name="inputnode"
    )
    inputnode.inputs.func_runs = func_runs

    # ---------------------------------------------------------------------
    # Level1Design
    # ---------------------------------------------------------------------
    level1design = Node(Level1Design(), name="level1design")

    level1design.inputs.timing_units = "secs"
    level1design.inputs.interscan_interval = tr
    level1design.inputs.bases = {"hrf": {"derivs": [0, 0]}}
    level1design.inputs.model_serial_correlations = "AR(1)"
    #level1design.inputs.high_pass_filter_cutoff = hpf
    level1design.inputs.session_info = session_info

    # ---------------------------------------------------------------------
    # EstimateModel
    # ---------------------------------------------------------------------
    level1estimate = Node(EstimateModel(), name="level1estimate")
    level1estimate.inputs.estimation_method = {"Classical": 1}

    # ---------------------------------------------------------------------
    # EstimateContrast
    # ---------------------------------------------------------------------
    contrastestimate = Node(EstimateContrast(), name="contrastestimate")
    contrastestimate.inputs.contrasts = contrasts

    # ----------------------------
    # DataSink
    # ----------------------------
    datasink = Node(DataSink(), name="datasink")
    datasink.inputs.base_directory = output_dir

    # Optional: remove hash folders
    datasink.inputs.parameterization = False


    # ---------------------------------------------------------------------
    # Connections
    # ---------------------------------------------------------------------
    wf.connect(level1design, "spm_mat_file", level1estimate, "spm_mat_file")
    wf.connect(level1estimate, "spm_mat_file", contrastestimate, "spm_mat_file")
    wf.connect(level1estimate, "beta_images", contrastestimate, "beta_images")
    wf.connect(level1estimate, "residual_image", contrastestimate, "residual_image")

    # Save outputs
    wf.connect(contrastestimate, "spm_mat_file",
               datasink, f"{name}.@spmmat")
    
    wf.connect(level1estimate, "beta_images",
               datasink, f"{name}.@beta")
    wf.connect(contrastestimate, "con_images",
               datasink, f"{name}.@con")
    wf.connect(contrastestimate, "spmT_images",
               datasink,f"{name}.@spmT")

    return wf


def run_stats(fmri_files, out_directory, working_dir, acq_info):
    logger.info("Launch stats generation")

    for func_run in fmri_files:
        func_name = os.path.basename(func_run).split('.')[0]
        tr = acq_info["general"]["tr"]
        events_tsv = func_run.replace("bold.nii.gz", "events.tsv").replace("bold.nii", "events.tsv")
        preproc_func_run = os.path.join(
            os.path.dirname(func_run).replace("raw","spm_preprocessing"), "smooth", "swar" + func_name +".nii"
        )
        motion_file  = os.path.join(
            os.path.dirname(func_run).replace("raw","spm_preprocessing"), "realign", "rp_" + func_name +  ".txt"
        )
        if not os.path.exists(preproc_func_run):
            raise FileNotFoundError(f"preprocessing not done: {preproc_func_run}")
        
        task_name = re.search(r"task-([^_]+)", func_run).group(1)

        session_info = build_session_info_single_run(
            task_name,
            preproc_func_run,
            events_tsv,
            motion_file,
            tmod=0,
            orth=1,
            hpf=128
        )
        if task_name == "gene":
            contrast_definitions = [
                {
                    "name": "GENE-CONTROL",
                    "type": "T",
                    "conditions": ["GENE", "CONTROL"],
                    "weights": [1, -1]
                },
                {
                    "name": "GENE",
                    "type": "T",
                    "conditions": ["GENE"],
                    "weights": [2]
                }
            ]
        elif task_name == "reco":
            contrast_definitions = [
                {
                    "name": "OLD-CONTROL",
                    "type": "T",
                    "conditions": ["OLD", "CONTROL"],
                    "weights": [1, -1]
                },
                {
                    "name": "OLD",
                    "type": "T",
                    "conditions": ["OLD"],
                    "weights": [1]
                }
            ]
        elif task_name == "rappel":
            contrast_definitions = [
                {
                    "name": "RAPPEL",
                    "type": "T",
                    "conditions": ["RAPPEL"],
                    "weights": [1]
                }
            ]
        elif task_name in ["langAud", "langVis"]:
            contrast_definitions = [
                {
                    "name": "LANG",
                    "type": "T",
                    "conditions": ["LANGAGE"],
                    "weights": [1]
                }
            ]
        elif task_name in ["clin"]:
            contrast_definitions = [
                {
                    "name": "CLIN",
                    "type": "T",
                    "conditions": ["CLIN"],
                    "weights": [1]
                }
            ]
        elif task_name in ["handmotor"]:
            contrast_definitions = [
                {
                    "name": "MOTOR vs REST",
                    "type": "T",
                    "conditions": ["MOTOR", "REST"],
                    "weights": [1, -1]
                }
            ]


        contrasts = build_contrasts(contrast_definitions)

        name = "stats_" + task_name

        if "run" in func_name:
            nb = re.search(r"run-([^_]+)",func_name).group(1)
            name += f"_run-{nb}"

        wf = create_stats_workflow(
            name=name,
            output_dir=out_directory,
            working_dir=working_dir,
            func_runs=preproc_func_run,
            tr=tr,
            session_info=session_info,
            contrasts=contrasts
        )

        # Run workflow
        wf.run()
        archive_spm_scripts(
            working_dir=wf.base_dir,
            out_dir=out_directory
        )
        logger.info(f"Stats  done for task : {task_name}")

    return 