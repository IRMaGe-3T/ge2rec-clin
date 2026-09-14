import os
import itertools
import math
import logging


from nipype import Node, Workflow
from nipype.interfaces.io import DataSink
from nipype.interfaces.spm import (
    Realign,
    SliceTiming,
    Coregister,
    NewSegment,
    Normalize12,
    Smooth
)
from nipype.interfaces.utility import IdentityInterface


from useful import archive_spm_scripts

logger = logging.getLogger(__name__)


def create_preproc_workflow(
    fmri_files,
    anat_file,
    output_dir,
    working_dir,
    tr,
    slice_order,
    ref_slice,
    voxel_size_fmri,
    spm_path,
    name
):
    """
    Create a Nipype workflow for SPM preprocessing.

    Parameters
    ----------
    fmri_files : list of str
        List of 4D fMRI NIfTI files (flexible length).
    anat_file : str
        Path to T1 anatomical image.
    output_dir : str
        Directory where results will be stored.
    tr : float
        Repetition time in seconds.
    slice_order : list of int
        Slice acquisition order.
    ref_slice : int
        Reference slice for slice timing.
    voxel_size : list of 3 float
         3-element list representing the voxel sizes (in mm) of the written normalised functional images
    spm_path:

    name : 
    """

    wf = Workflow(name=f"spm_preprocessing_{name}")
    wf.base_dir = working_dir

    # ---------------------------------------------------------------------
    # Input node (flexible number of fMRI runs)
    # ---------------------------------------------------------------------
    inputnode = Node(
        IdentityInterface(fields=["fmri_files", "anat_file"]),
        name="inputnode"
    )
    inputnode.inputs.fmri_files = fmri_files
    inputnode.inputs.anat_file = anat_file

    # ---------------------------------------------------------------------
    # 1) Realign
    # ---------------------------------------------------------------------
    realign = Node(Realign(), name="realign")
    realign.inputs.register_to_mean = True

    # ---------------------------------------------------------------------
    # 2) Slice Timing
    # ---------------------------------------------------------------------
    slicetiming = Node(SliceTiming(), name="slicetiming")
    slicetiming.inputs.num_slices = len(slice_order)
    slicetiming.inputs.time_repetition = tr
    slicetiming.inputs.time_acquisition = tr - (tr / len(slice_order))
    slicetiming.inputs.slice_order = slice_order
    slicetiming.inputs.ref_slice = ref_slice

    # ---------------------------------------------------------------------
    # 3) Coregister (mean functional -> T1)
    # ---------------------------------------------------------------------
    coreg = Node(Coregister(), name="coreg")
    coreg.inputs.jobtype = "estimate"

    # ---------------------------------------------------------------------
    # 4) NewSegment on coregistered T1
    # ---------------------------------------------------------------------
    segment = Node(NewSegment(), name="segment")
    segment.inputs.channel_info = (
        0.001,
        60.0,
        (False, True),
    )
    segment.inputs.write_deformation_fields = [False, True]

    tpm_path = os.path.join(
            spm_path, "tpm", "TPM.nii"
        )
    tissues_list = [
            ((tpm_path, 1), 1, (True, False), (False, False)),
            ((tpm_path, 2), 1, (True, False), (False, False)),
            ((tpm_path, 3), 2, (True, False), (False, False)),
            ((tpm_path, 4), 3, (True, False), (False, False)),
            ((tpm_path, 5), 4, (True, False), (False, False)),
            ((tpm_path, 6), 2, (True, False), (False, False)),
        ]
    segment.inputs.tissues = tissues_list
    # ---------------------------------------------------------------------
    # 5) Normalize functional images using deformation field
    # ---------------------------------------------------------------------
    normalize_func = Node(Normalize12(), name="normalize_func")
    normalize_func.inputs.jobtype = "write"
    normalize_func.inputs.write_voxel_sizes = voxel_size_fmri

    # ---------------------------------------------------------------------
    # 6) Normalize anatomical image
    # ---------------------------------------------------------------------
    normalize_anat = Node(Normalize12(), name="normalize_anat")
    normalize_anat.inputs.jobtype = "write"
    normalize_anat.inputs.write_voxel_sizes = [1.0, 1.0, 1.0]

    # ---------------------------------------------------------------------
    # 7) Smooth normalized functional images
    # ---------------------------------------------------------------------
    smooth = Node(Smooth(), name="smooth")
    smooth.inputs.fwhm = [6, 6, 6]

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

    # Realign
    wf.connect(inputnode, "fmri_files", realign, "in_files")

    # Slice timing after realign
    wf.connect(realign, "realigned_files", slicetiming, "in_files")

    # Coregistration
    wf.connect(inputnode, "anat_file", coreg, "source")
    wf.connect(realign, "mean_image", coreg, "target")

    # Segmentation on T1
    wf.connect(coreg, "coregistered_source", segment, "channel_files")

    # Normalize functional images
    wf.connect(segment, "forward_deformation_field", normalize_func, "deformation_file")
    wf.connect(slicetiming, "timecorrected_files", normalize_func, "apply_to_files")
    #wf.connect(coreg, "coregistered_files", normalize_func, "apply_to_files")

    # Normalize anatomical image
    wf.connect(segment, "forward_deformation_field", normalize_anat, "deformation_file")
    wf.connect(segment, "bias_corrected_images", normalize_anat, "apply_to_files")

    # Smooth normalized functional images
    wf.connect(normalize_func, "normalized_files", smooth, "in_files")


    # Save outputs
    wf.connect(realign, "realignment_parameters",
               datasink, "realign.@rp")

    wf.connect(realign, "mean_image",
               datasink, "realign.@mean")
    
    wf.connect(realign, "realigned_files",
               datasink, "realign.@realignedfiles")
    
    wf.connect(coreg, "coregistered_source",
               datasink, "coreg.@coregisteredsource")
    
    wf.connect(slicetiming, "timecorrected_files",
               datasink, "slicetiming.@timecorrectedfiles")
    
    wf.connect(segment, "bias_corrected_images",
               datasink, "segment.@biascorimage")
    
    wf.connect(segment, "forward_deformation_field",
               datasink, "segment.@forward")
    
    wf.connect(normalize_anat, "normalized_files",
               datasink, "normalize_anat.@normalizedfiles")
    
    wf.connect(normalize_func, "normalized_files",
               datasink, "normalize_func.@normalizedfiles")

    wf.connect(smooth, "smoothed_files",
               datasink, "smooth.@files")

    return wf


def get_slice_order(acquisition_type, num_slices, repetion_time): 

    if acquisition_type == "sequential ascending":
        slice_order = list(range(1, num_slices + 1))

    if acquisition_type == "sequential descending":
        slice_order = list(range(num_slices, 0, -1))

    if acquisition_type == "interleaved (middle-top)":
        slice_order = []

        for a, b in (itertools.zip_longest)(
            list(range(math.ceil(num_slices / 2), 0, -1)),
            list(
                range(
                    math.ceil(num_slices),
                    math.ceil(num_slices / 2),
                    -1,
                )
            ),
        ):
            if (num_slices % 2) == 0:
                slice_order.append(b)
                slice_order.append(a)

            else:
                slice_order.append(a)
                slice_order.append(b)

        if None in slice_order:
            slice_order.remove(None)

    if acquisition_type == "interleaved (bottom-up)":
        slice_order = list(
            range(1, num_slices + 1, 2)
        ) + list(range(2, num_slices + 1, 2))

    if acquisition_type == "interleaved (top-down)":
        slice_order = list(range(num_slices, 0, -2)) + list(
            range(num_slices - 1, 0, -2)
        )
    slice_order = [
        (i - 1) * (float(repetion_time) / num_slices) * 1000
        for i in slice_order
    ]
    return slice_order


def get_ref_slice(acquisition_type, num_slices):
    if (
        acquisition_type == "sequential ascending"
        or acquisition_type == "sequential descending"
        ):
        ref_slice = math.ceil(num_slices / 2)            
    else:
        ref_slice = 1
    return ref_slice


def sort_by_task(file_list):
    """
    Sort BOLD filenames according to task order:
    gene -> reco -> rappel
    """
    task_order = {
        "task-gene": 0,
        "task-reco": 1,
        "task-rappel": 2,
    }

    def get_task_index(filename):
        for key in task_order:
            if key in filename:
                return task_order[key]
        return 99  # si une task inconnue apparaît

    return sorted(file_list, key=get_task_index)


def run_preprocessing(anat_file, fmri_files, preproc_directory, working_dir, acquisition_type, spm_path, acq_info, name):
    logger.info("Launch preprocessing ")

    repetition_time = acq_info["general"]["tr"]
    num_slices =  acq_info["general"]["num_slices"]
    voxel_size_round =  acq_info["general"]["voxel_size_round"]
    slice_order = get_slice_order(acquisition_type, num_slices, repetition_time)
    ref_slice = get_ref_slice(acquisition_type, num_slices)

    # Create preproc workflow
    wf = create_preproc_workflow(
        fmri_files=sort_by_task(fmri_files),
        anat_file=anat_file,
        output_dir=preproc_directory,
        working_dir=working_dir,
        tr =repetition_time,
        slice_order=slice_order,
        ref_slice=ref_slice,
        voxel_size_fmri = voxel_size_round,
        spm_path=spm_path, 
        name=name
    )

    # Run workflow
    wf.run()
    archive_spm_scripts(
        working_dir=wf.base_dir,
        out_dir=os.path.dirname(preproc_directory)
    )
    logger.info(f"Preprocessing done for {name}")



                


