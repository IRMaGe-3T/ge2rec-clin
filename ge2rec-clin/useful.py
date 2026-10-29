import os
import subprocess
import json
import shutil
import gzip
import glob
import pydicom

import nibabel as nib
import uuid
from nilearn.image import resample_to_img
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colormaps
from matplotlib.colors import LinearSegmentedColormap
from mpl_toolkits.axes_grid1 import ImageGrid
from pydicom.tag import Tag
from math import pi, sqrt



def archive_spm_scripts(working_dir, out_dir):

    spm_files = glob.glob(
        os.path.join(working_dir, "**", "*.m"),
        recursive=True
    )

    if not spm_files:
        print("No spm files.")
        return

    dest_dir = os.path.join(out_dir, "spm_batches")
    os.makedirs(dest_dir, exist_ok=True)

   

    for f in spm_files:
        random_id = uuid.uuid4().hex[:8]
        base = os.path.basename(f)
        name, ext = os.path.splitext(base)

        new_name = f"{name}_{random_id}{ext}"
        dest_path = os.path.join(dest_dir, new_name)
        shutil.copy2(f, dest_path)

    print(f"{len(spm_files)} SPM files archived.")



def check_file_ext(in_file, ext_dic):
    """Check file extension

    :param in_file: file name (a string)
    :param ext_dic: dictionary of the valid extensions for the file
                    (dictionary, ex:
                    EXT = {"NIFTI_GZ": "nii.gz", "NIFTI": "nii"})
    :returns:
        - valid_bool: True if extension is valid (a boolean)
        - in_ext: file extension (a string)
        - file_name: file name without extension (a string)
    """

    # Get file extension
    valid_bool = False
    ifile = os.path.split(in_file)[-1]
    file_name, in_ext = ifile.rsplit(".", 1)
    if in_ext == "gz":
        (file_name_2, in_ext_2) = file_name.rsplit(".", 1)
        in_ext = in_ext_2 + "." + in_ext
        file_name = file_name_2

    valid_ext = list(ext_dic.values())

    if in_ext in valid_ext:
        valid_bool = True

    return valid_bool, in_ext, file_name


def execute_command(command):
    """Execute command"""
    print("\n", command)
    p = subprocess.Popen(
        command,
        shell=False,
        bufsize=-1,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
    )

    print("--------->PID:", p.pid)

    (sdtoutl, stderrl) = p.communicate()
    if str(sdtoutl) != "" and str(sdtoutl) != " ":
        print("sdtoutl: ", sdtoutl.decode())
    if str(stderrl) != "" and str(stderrl) != " ":
        print("stderrl: ", stderrl.decode())

    result = p.wait()

    return result, stderrl, sdtoutl


def find_dicom_tag_value(input_dicom_dataset, tag):
    """
    Find DICOM tag value
    """
    try:
        value = input_dicom_dataset[tag].value
    except ValueError:
        value = "tagNotFound"
    return value


def get_all_dicom_files(dicom_directory):
    """
    Get all DICOM files from a dirctory
    """
    if len(dicom_directory) == 0:
        message = "Input directory is empty."
        raise RuntimeError(message)

    raw_storage_methods_not_taken = [
        "1.2.840.10008.5.1.4.1.1.11.1",
        "1.2.840.10008.5.1.4.1.1.66",
        "Secondary Capture Image Storage",
        "1.2.840.10008.5.1.4.1.1.7",
    ]

    raw_input_files = os.listdir(dicom_directory)
    input_files = []

    # Test each file to check if it is DICOM
    for file_name in raw_input_files:
        file_start = file_name.split("/")[-1].split("_")[0].lower()
        file_ext = file_name.split(".")[-1]
        not_taken_start = ["xx", "ps", "dicomdir"]
        not_taken_ext = [
            "bvecs",
            "bvals",
            "txt",
        ]

        if file_start in not_taken_start or file_ext in not_taken_ext:
            print(f"File {file_name} not taken (not a DICOM).")
            continue
        elif os.path.isdir(os.path.join(dicom_directory, file_name)):
            # Add all files from subdirectory to file list
            sub_directory = os.path.join(dicom_directory, file_name)
            for file_in_directory in os.listdir(sub_directory):
                file_path = os.path.join(file_name, file_in_directory)
                raw_input_files.append(file_path)
            continue

        try:
            input_dicom = pydicom.dcmread(
                os.path.join(dicom_directory, file_name)
            )
        except Exception:
            print(f"File {file_name} not taken (coul not read DICOM).")
            continue
        storage_method = find_dicom_tag_value(input_dicom, Tag(0x08, 0x16))[0]
        if storage_method in raw_storage_methods_not_taken:
            print(f"File {file_name} not taken (bad storage method).")
            continue
        input_files.append(os.path.join(dicom_directory, file_name))
    return input_files


def get_value_json(json_path, field_name):
    """
    Get a value from a json for one filed

    json_path (string): json path
    field_name (string): field name (example: "Manufacturer")
    """
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            field = data[field_name]
    except Exception:
        field = "na"
    return field


def copy_and_unzip_niigz(input_files, output_dir, overwrite=False):
    """
    Copy .nii.gz files to a working directory and unzip them to .nii.
    Copy .json and .tsv 

    Parameters
    ----------
    input_files : list of str
        List of .nii.gz files.
    output_dir : str
        Destination directory.
    overwrite : bool
        Overwrite existing files if True.

    Returns
    -------
    list of str
        Absolute paths to unzipped .nii files.
    """

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    unzipped_files = []

    for file_path in input_files:

        if not os.path.exists(file_path):
            raise FileNotFoundError("Input file not found: {}".format(file_path))

        if not file_path.endswith(".nii.gz"):
            raise ValueError("File is not .nii.gz: {}".format(file_path))

        filename = os.path.basename(file_path)

        # Copy file
        copied_file = os.path.join(output_dir, filename)

        if overwrite or not os.path.exists(copied_file):
            shutil.copy2(file_path, copied_file)
            # Copy of .json
            json_path = file_path.replace(".nii.gz", ".json")
            if os.path.exists(json_path):
                copied_json_file = copied_file.replace(".nii.gz", ".json")
                shutil.copy2(json_path, copied_json_file)
            # Copy of .tsv
            tsv_path = file_path.replace("bold.nii.gz", "events.tsv")
            if os.path.exists(tsv_path):
                copied_tsv_file = copied_file.replace("bold.nii.gz", "events.tsv")
                shutil.copy2(tsv_path, copied_tsv_file)

        # Define uncompressed filename
        unzipped_name = filename.replace(".nii.gz", ".nii")
        unzipped_file = os.path.join(output_dir, unzipped_name)

        # Unzip file
        if overwrite or not os.path.exists(unzipped_file):
            with gzip.open(copied_file, "rb") as f_in:
                with open(unzipped_file, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(copied_file)

        unzipped_files.append(os.path.abspath(unzipped_file))

    return unzipped_files


def plot_slice_planes(
    data_1,
    data_2=None,
    plane="ax",
    fig_rows=4,
    fig_cols=4,
    slice_start=None,
    slice_step=None,
    dyn=1,
    cmap_1="Greys_r",
    vmin_1=None,
    vmax_1=None,
    cmap_2="rainbow",
    vmin_2=None,
    vmax_2=None,
    out_dir=None,
    only_noise=False,
    out_name=None,
    convention="neurological"
):
    """Create a PNG file with a mosaic display of volume slices.

    Several images can be overlaid. data_1, the only mandatory argument,
    is the background image (or the only image displayed). data_2 is the
    image (or images) superimposed on data_1.

    fig_rows, fig_cols, slice_start and slice_step are optional. If they are
    not known, plot_slice_planes will try to adapt as best it can to obtain
    an acceptable display. The default values for fig_rows, fig_cols and dyn
    are 4, 4 and 1 respectively.

    :param data_1: an existing, image file (valid extensions: .nii).
    :param data_2: an existing, image file or a list of existing image files
                   (valid extensions: .nii).
    :param plane: orientation plane (ax, sag or cor)
    :param fig_rows: the number of rows in the images panel (integer).
    :param fig_cols: the number of columns in the images panel (integer).
    :param slice_start: starting slice number to be displayed (integer).
    :param slice_step: the gap between each slice to be displayed (integer).
    :param dyn: the volume number in the space-time, for 4D (integer).
    :param cmap_1: the color map name (string) for data_1.
    :param vmin_1: the low value of the range used for data_1 display(float).
    :param vmax_1: the high value of the range used for data_1 display(float).
    :param cmap_2: the color map name (string) or a list of RGB tuple
                   (ex. [(255, 0, 0), (0, 0, 255)]).
    :param vmin_2: the low value of the range used for data_2 display(float).
    :param vmax_2: the high value of the range used for data_2 display(float).
    :param out_dir: the output directory where the mosaic images will be saved.
    :param only_noise: if True, shows the noise (boolean).
    :param out_name: the suffix added to form the output name (string).
    :param convention: radilogical or neurological(string)

    Note: cmap for parametric display can be, gist_rainbow, RdYlBu, Spectral,
          rainbow_r, jet_r, seismic_r, bwr_r
    """

    if plane not in ["ax", "cor", "sag"]:
        print("Parameter plane should be either ax, sag or cor")
        return

    brain_img_1 = nib.as_closest_canonical(nib.load(data_1))
    brain_data_1 = brain_img_1.get_fdata()
    brain_data_1 = np.squeeze(brain_data_1)

    if convention not in ("neurological", "radiological"):
        raise ValueError(
            "convention must be 'neurological' or 'radiological'"
        )

    if plane in ("ax", "cor"):
        if convention == "neurological":
            left_label, right_label = "L", "R"
        else:
            left_label, right_label = "R", "L"

    elif plane == "sag":
        # The horizontal axis represents posterior-anterior.
        left_label, right_label = "P", "A"
        if cmap_1 is None:
            cmap_1 = "Greys_r"

    cmap_1 = colormaps.get_cmap(cmap_1)
    cmap_1.set_bad(color="black")
    brain_data_2 = None

    if data_2 is not None:
        brain_data_2 = []
        cmap_2_tmp = []
        vmin_2_tmp = []
        vmax_2_tmp = []

        if not isinstance(data_2, list):
            data_2 = [data_2]

        for i, fil in enumerate(data_2):
            brain_img_2 = nib.as_closest_canonical(nib.load(fil))

            if brain_img_1.shape[:3] != brain_img_2.shape[:3]:
                brain_img_2 = resample_to_img(
                    brain_img_2, brain_img_1, interpolation="linear"
                )

            data = brain_img_2.get_fdata().astype(np.float32)

            data = np.squeeze(data)
            nan_indexes = np.isnan(data)

            if cmap_2 is None:
                cmap = "rainbow"

            elif isinstance(cmap_2, str):
                cmap = cmap_2

            if isinstance(cmap_2, list):
                cmap = cmap_2[int(np.fix(i / 2))]
                norm_mask_color = tuple(channel / 255 for channel in cmap)
                cmap = LinearSegmentedColormap.from_list(
                    "CustomCmap", [norm_mask_color, norm_mask_color]
                )

            else:
                cmap = colormaps.get_cmap(cmap)

            cmap.set_bad(alpha=0)

            if vmin_2 is None:
                vmin = np.min(data[~nan_indexes])

            else:
                vmin = vmin_2

            if vmin < 0:
                vmin = 0.1

            if vmax_2 is None:
                vmax = np.max(data[~nan_indexes])

            else:
                vmax = vmax_2

            brain_data_2.append(data)
            cmap_2_tmp.append(cmap)
            vmin_2_tmp.append(vmin)
            vmax_2_tmp.append(vmax)

        cmap_2 = cmap_2_tmp
        vmin_2 = vmin_2_tmp
        vmax_2 = vmax_2_tmp

    if len(brain_data_1.shape) == 4:
        brain_data_1 = brain_data_1[:, :, :, dyn]

    elif len(brain_data_1.shape) > 4:
        # TODO: what we do in this case?
        pass

    min_thres = np.percentile(brain_data_1, 5)
    mask_data_1 = np.ones_like(brain_data_1)
    mask_data_1[brain_data_1 <= min_thres] = 0
    ind_non_zero = np.argwhere(mask_data_1)
    (ystart, xstart, zstart), (ystop, xstop, zstop) = (
        ind_non_zero.min(0),
        ind_non_zero.max(0) + 1,
    )
    brain_data_1 = brain_data_1[ystart:ystop, xstart:xstop, zstart:zstop]
    mask_data_1 = np.logical_not(np.isnan(brain_data_1))

    if only_noise:
        vmin_1 = np.percentile(brain_data_1[mask_data_1], 0)
        vmax_1 = np.percentile(brain_data_1[mask_data_1], 61)

    if vmin_1 is None:
        vmin_1 = np.percentile(brain_data_1[mask_data_1], 0.5)

    if vmax_1 is None:
        vmax_1 = np.percentile(brain_data_1[mask_data_1], 99.5)

    disp_slices = fig_rows * fig_cols

    slice_axis = {
        "ax": 2,
        "cor": 1,
        "sag": 0,
    }[plane]

    lst = np.arange(brain_data_1.shape[slice_axis])

    if slice_start:
        # fmt: off
        lst = lst[slice_start - 1 if slice_start != 0 else 0:]
        # fmt: on

    start = 0
    ind_slices = []

    if disp_slices > len(lst):
        disp_slices = len(lst)

    if slice_step is None:
        avg = len(lst) // disp_slices
        remainder = len(lst) % disp_slices

    else:
        avg = slice_step
        remainder = -1

    for i in range(disp_slices):
        end = start + avg + (1 if i < remainder else 0)

        if start >= len(lst):
            break

        ind_slices.append(lst[start:end])
        start = end

    if all(
        (isinstance(element, np.ndarray) and len(element) == 1)
        for element in ind_slices
    ):
        ind_slices = [element[0] for element in ind_slices]

    else:
        middle_idx = [(len(element) - 1) // 2 for element in ind_slices]
        ind_slices = [
            element[idx] for element, idx in zip(ind_slices, middle_idx)
        ]

    # Reminder: 19cm == 7.4803inch; 23cm == 9.0551
    # Width, height in inches
    fig = plt.figure(figsize=(7.4803, 9.0551), facecolor="black")
    # fig.patch.set_facecolor("black")
    zooms = brain_img_1.header.get_zooms()

    if brain_data_2 is None or len(brain_data_2) > 1:
        grid = ImageGrid(
            fig,
            111,
            nrows_ncols=(fig_rows, fig_cols),
            axes_pad=0,
        )
    elif len(brain_data_2) == 1:
        grid = ImageGrid(
            fig,
            111,
            nrows_ncols=(fig_rows, fig_cols),
            axes_pad=0,
            cbar_mode="single",
            cbar_location="bottom",
            cbar_pad=0,
            cbar_size="2%",
        )

    if disp_slices < 5:
        fontsize = 18

    elif disp_slices < 10:
        fontsize = 16

    elif disp_slices < 15:
        fontsize = 14

    elif disp_slices < 20:
        fontsize = 12

    elif disp_slices < 25:
        fontsize = 10

    elif disp_slices < 40:
        fontsize = 8

    elif disp_slices < 100:
        fontsize = 6

    else:
        fontsize = 4

    for slice_numb, ax in enumerate(grid):

        if slice_numb >= len(ind_slices):
            displ_1 = np.zeros((2, 2, 2))
            ind_slice = 1

            if brain_data_2 is not None:
                displ_2 = [np.zeros((2, 2, 2))]

            else:
                displ_2 = None

        else:
            displ_1 = brain_data_1
            ind_slice = ind_slices[slice_numb]
            displ_2 = brain_data_2

        if plane == "ax":
            phys_sp = np.array(zooms[:2]) * brain_data_1[:, :, ind_slice].shape
            data =np.swapaxes(displ_1[:, :, ind_slice], 0, 1)
            if convention == "radiological":
                data = np.fliplr(data)
            ax.imshow(
                data,
                vmin=vmin_1,
                vmax=vmax_1,
                cmap=cmap_1,
                interpolation="nearest",
                origin="lower",
                extent=[0, phys_sp[0], 0, phys_sp[1]],
            )
        elif plane == "sag":
            phys_sp = np.array(zooms[:2]) * brain_data_1[ind_slice, :, :].shape
            data = np.swapaxes(displ_1[ind_slice, :, :], 0, 1)
            ax.imshow(
                data,
                vmin=vmin_1,
                vmax=vmax_1,
                cmap=cmap_1,
                interpolation="nearest",
                origin="lower",
                extent=[0, phys_sp[0], 0, phys_sp[1]],
            )
        elif plane == "cor":
            phys_sp = np.array(zooms[:2]) * brain_data_1[:, ind_slice, :].shape
            data = np.swapaxes(displ_1[:, ind_slice, :], 0, 1)
            if convention == "radiological":
                data = np.fliplr(data)
            ax.imshow(
                data,
                vmin=vmin_1,
                vmax=vmax_1,
                cmap=cmap_1,
                interpolation="nearest",
                origin="lower",
                extent=[0, phys_sp[0], 0, phys_sp[1]],
            )

        if displ_2 is not None:

            for i, displ in enumerate(displ_2):
                if plane == "ax":
                    data = np.swapaxes(displ[:, :, ind_slice], 0, 1)
                    if convention == "radiological":
                        data = np.fliplr(data)
                    im2 = ax.imshow(
                        data,
                        vmin=vmin_2[i],
                        vmax=vmax_2[i],
                        cmap=cmap_2[i],
                        alpha=np.where(data <= vmin_2[i], 0, 0.5),
                        # alpha=np.where(data <= vmin_2[i], 0, 1.0),
                        interpolation="nearest",
                        origin="lower",
                        extent=[0, phys_sp[0], 0, phys_sp[1]],
                    )
                elif plane == "sag":
                    data = np.swapaxes(displ[ind_slice, :, :], 0, 1)
                    im2 = ax.imshow(
                        data,
                        vmin=vmin_2[i],
                        vmax=vmax_2[i],
                        cmap=cmap_2[i],
                        alpha=np.where(data <= vmin_2[i], 0, 0.5),
                        # alpha=np.where(data <= vmin_2[i], 0, 1.0),
                        interpolation="nearest",
                        origin="lower",
                        extent=[0, phys_sp[0], 0, phys_sp[1]],
                    )
                elif plane == "cor":
                    data = np.swapaxes(displ[:, ind_slice, :], 0, 1)
                    if convention == "radiological":
                        data = np.fliplr(data)
                    im2 = ax.imshow(
                        data,
                        vmin=vmin_2[i],
                        vmax=vmax_2[i],
                        cmap=cmap_2[i],
                        alpha=np.where(data <= vmin_2[i], 0, 0.5),
                        # alpha=np.where(data <= vmin_2[i], 0, 1.0),
                        interpolation="nearest",
                        origin="lower",
                        extent=[0, phys_sp[0], 0, phys_sp[1]],
                    )

        ax.set_xticklabels([])
        ax.set_yticklabels([])
        ax.grid(False)
        ax.axis("off")
   
        bgcolor = cmap_1(min(vmin_1, 0.0))
        fgcolor = cmap_1(vmax_1)

        if slice_numb + 1 > len(ind_slices):
            ind_slice = ""

        ax.text(
            0.98,
            0.01,
            f"{ind_slice}",
            color=fgcolor,
            transform=ax.transAxes,
            horizontalalignment="right",
            verticalalignment="bottom",
            fontsize=fontsize,
            bbox=dict(
                boxstyle="square,pad=0", edgecolor=bgcolor, facecolor=bgcolor
            ),
        )
    # --- Add orientation markers on the first row only ---
    left_ax = grid[0]
    right_ax = grid[fig_cols - 1]

    left_ax.text(
        0.02, 0.98,
        left_label,
        transform=left_ax.transAxes,
        color="white",
        fontsize=fontsize,
        fontweight="bold",
        alpha=0.6,
        ha="left",
        va="top",
    )

    right_ax.text(
        0.98, 0.98,
        right_label,
        transform=right_ax.transAxes,
        color="white",
        fontsize=fontsize,
        fontweight="bold",
        alpha=0.6,
        ha="right",
        va="top",
    )

    if brain_data_2 is not None and len(brain_data_2) == 1:
        cbar = grid.cbar_axes[0].colorbar(im2)
        cbar.ax.tick_params(labelsize=6, colors="white")
        cbar.set_label("Intensity", size=6, color="white")

    if data_2 is None:
        fname, _ = os.path.splitext(os.path.basename(data_1))

    elif len(brain_data_2) > 1:
        fname = ""

    else:
        fname, _ = os.path.splitext(os.path.basename(data_2[0]))

    if out_name is not None:
        fname += "_" + out_name

    if out_dir is None:
        out_dir = os.path.dirname(data_1)

    out_file = os.path.join(out_dir, fname + "_slice_planes_plot.png")
    counter = 1

    while os.path.exists(out_file):
        b_name, ext = os.path.splitext(out_file)
        out_file = f"{b_name}_{counter:03d}{ext}"
        counter += 1

    fig.savefig(out_file, format="png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out_file


def plot_orthogonal_mosaics(
    data_1,
    data_2=None,
    slices=None,
    cmap_1="gray",
    vmin_1=None,
    vmax_1=None,
    cmap_2="hot",
    color_2=None,
    vmin_2=None,
    vmax_2=None,
    alpha=0.6,
    out_dir=None,
    out_name="orthogonal_mosaics",
    dpi=200,
):
    """
    Create a PNG containing axial, sagittal and coronal slice mosaics.

    Parameters
    ----------
    data_1 : str
        Path to the background NIfTI image.

    data_2 : str or None
        Path to the overlay NIfTI image.

    slices : dict or None
        Slice indices to display in each orientation.
        Indices refer to the canonical image axes.

        Example:
        {
            "ax": 40, ,
            "sag": 70,
            "cor": 80
        }

        If None, the image center are displayed
        for each orientation.

    cmap_1 : str
        Background colormap.

    vmin_1, vmax_1 : float or None
        Background intensity range. If None, percentiles are used.

    cmap_2 : str
        Overlay colormap.

    color_2 : str
        Overlay color.

    vmin_2, vmax_2 : float or None
        Overlay intensity range. If None, percentiles are used.

    alpha : float
        Overlay transparency, between 0 and 1.

    out_dir : str or None
        Output directory. Defaults to the directory containing data_1.

    out_name : str
        Output filename without extension.

    dpi : int
        PNG resolution.

    Returns
    -------
    str
        Path to the generated PNG file.
    """

    # --------------------------------------------------
    # Load images and use a consistent orientation
    # --------------------------------------------------
    img_1 = nib.as_closest_canonical(nib.load(data_1))
    vol_1 = np.squeeze(img_1.get_fdata())

    if vol_1.ndim != 3:
        raise ValueError("data_1 must contain a 3D image.")

    vol_2 = None

    if data_2 is not None:
        img_2 = nib.load(data_2)

        # Resample overlay to the background image if necessary
        if (
            img_1.shape[:3] != img_2.shape[:3]
            or not np.allclose(img_1.affine, img_2.affine)
        ):
            img_2 = resample_to_img(
                img_2,
                img_1,
                interpolation="continuous",
            )

        vol_2 = np.squeeze(img_2.get_fdata())

        if vol_2.ndim != 3:
            raise ValueError("data_2 must contain a 3D image.")

    # --------------------------------------------------
    # Intensity ranges
    # --------------------------------------------------
    valid_1 = vol_1[np.isfinite(vol_1)]

    if vmin_1 is None:
        vmin_1 = np.percentile(valid_1, 1)

    if vmax_1 is None:
        vmax_1 = np.percentile(valid_1, 99)

    if vol_2 is not None:
        valid_2 = vol_2[np.isfinite(vol_2)]

        if vmin_2 is None:
            vmin_2 = np.percentile(valid_2, 1)

        if vmax_2 is None:
            vmax_2 = np.percentile(valid_2, 99)

    # --------------------------------------------------
    # Slice selection
    # --------------------------------------------------
    orientations = {
        "ax": {
            "title": "Axial",
            "axis": 2,
            "extract": lambda vol, i: vol[:, :, i].T,
        },
        "sag": {
            "title": "Sagittal",
            "axis": 0,
            "extract": lambda vol, i: vol[i, :, :].T,
        },
        "cor": {
            "title": "Coronal",
            "axis": 1,
            "extract": lambda vol, i: vol[:, i, :].T,
        },
    }

    if slices is None:
        slices = {
            "ax": vol_1.shape[2] // 2,
            "sag": vol_1.shape[0] // 2,
            "cor": vol_1.shape[1] // 2,
        }

    for key, orientation in orientations.items():
        axis = orientation["axis"]
        idx = slices[key]

        if not 0 <= idx < vol_1.shape[axis]:
            raise ValueError(
                f"Slice index for {key} must be between 0 "
                f"and {vol_1.shape[axis] - 1}."
            )

    # --------------------------------------------------
    # Plot the three mosaics
    # --------------------------------------------------
    fig, axes = plt.subplots(
        1, 3,
        figsize=(12, 4),
        facecolor="black",
    )

    for ax, (key, orientation) in zip(axes, orientations.items()):
        idx = slices[key]
        ax.set_facecolor("black")
        ax.axis("off")

        background = orientation["extract"](vol_1, idx)

        ax.imshow(
            np.ma.masked_invalid(background),
            cmap=cmap_1,
            vmin=vmin_1,
            vmax=vmax_1,
            origin="lower",
            interpolation="nearest",
        )

        # Overlay
        if vol_2 is not None:
            overlay = orientation["extract"](vol_2, idx)

            # Display all non-zero mask voxels
            mask = np.isfinite(overlay) & (overlay != 0)

            if color_2 is not None:
                # Single color for all mask labels
                rgba = np.zeros((*overlay.shape, 4))
                rgba[mask] = (*plt.matplotlib.colors.to_rgb(color_2), alpha)

                ax.imshow(
                    rgba,
                    origin="lower",
                    interpolation="nearest",
                )

            else:
                # Colormap for parametric maps
                overlay = np.ma.masked_where(
                    ~mask,
                    overlay,
                )

                ax.imshow(
                    overlay,
                    cmap=cmap_2,
                    vmin=vmin_2,
                    vmax=vmax_2,
                    alpha=alpha,
                    origin="lower",
                    interpolation="nearest",
                )

        ax.set_title(
            f"{idx}",
            color="white",
        )

    fig.tight_layout()
    # --------------------------------------------------
    # Save PNG
    # --------------------------------------------------
    if out_dir is None:
        out_dir = os.path.dirname(os.path.abspath(data_1))

    os.makedirs(out_dir, exist_ok=True)

    out_file = os.path.join(out_dir, f"{out_name}.png")

    fig.savefig(
        out_file,
        dpi=dpi,
        bbox_inches="tight",
        facecolor="black",
    )

    plt.close(fig)

    return out_file

def plot_realignment_parameters(
    realignment_parameters,
    vox_size,
    out_file_tra,
    out_file_rot,
    figsize=(12, 5.6),
):
    """
    Plot SPM realignment parameters.

    :param realignment_parameters: realignment parameters file
                                   (a string representing an existing file) or
                                   realignment parameters (a numpy.ndarray
                                   object with shape[1] == 6)
    :param vox_size: voxel size of the data (a list of 3 float or integer)
    :param out_file_tra: out path for the translation figure (a string
                         representing a path file)
    :param out_file_rot: out path for the rotation figure (a string
                         representing a path file)
    :param figsize: width, height of parametric maps plot, in inches (float,
                    float)

    :returns:
        - qc: result of the quality check (a boolean). True: OK

    """
    # TODO: it seems that this function is not sufficiently protected against
    #       exceptions being thrown

    qc = False
    (
        rmsdTra,
        maxRmsdTra,
        maxTra,
        maxTraCheck,
        minTra,
        rmsdRot,
        maxRmsdRot,
        maxRot,
        maxRotCheck,
        minRot,
    ) = np.zeros(10)

    # Ensure realignment_parameters is a valid path or a NumPy array with
    # the expected shape
    if isinstance(
        realignment_parameters, (str, os.PathLike)
    ) and os.path.exists(realignment_parameters):
        # If it's a valid file path, load the data
        data_rp = np.loadtxt(realignment_parameters)

    elif isinstance(realignment_parameters, np.ndarray):

        # If it's a NumPy array, check if it has the expected shape
        if (
            realignment_parameters.size > 0
            and realignment_parameters.shape[1] == 6
        ):
            data_rp = realignment_parameters

        else:
            raise ValueError(
                "The NumPy array must have 6 columns and " "non-zero size."
            )

    else:
        # TODO: perhaps we should protect the next steps if
        #  realignment_parameters is neither an existing file
        #  nor a numpy array?
        pass

    data_rp[:, 3:] = data_rp[:, 3:] * 180 / pi  # Rad to deg conversion
    xLim = len(data_rp) + 1
    # Create x-values starting from 1
    x_values = np.arange(1, len(data_rp) + 1)

    for i in range(3):
        for n in data_rp[:, i]:
            rmsdTra = rmsdTra + n**2

        rmsdTra = sqrt(rmsdTra / len(data_rp[:, i]))

        if rmsdTra > maxRmsdTra:
            # maxRmsdTra: Maximum root-mean-square deviation for
            # x, y, z linear motion
            maxRmsdTra = rmsdTra

        rmsdTra = 0

        if max(data_rp[:, i]) > maxTra:
            # maxTra: Maximum x, y, z linear motion in
            # POSITIVE direction
            maxTra = max(data_rp[:, i])

        if min(data_rp[:, i]) < minTra:
            # minTra: Maximum x, y, z linear motion in
            # NEGATIVE direction
            minTra = min(data_rp[:, i])

    maxTraCheck = maxTra

    if abs(minTra) > maxTra:
        maxTraCheck = abs(minTra)

    for i in range(3, 6):
        for n in data_rp[:, i]:
            rmsdRot = rmsdRot + n**2

        rmsdRot = sqrt(rmsdRot / len(data_rp[:, i]))

        if rmsdRot > maxRmsdRot:
            # maxRmsdRot: Maximum root-mean-square deviation for
            # roll, pitch, yaw rotational motion
            maxRmsdRot = rmsdRot

        rmsdRot = 0

        if max(data_rp[:, i]) > maxRot:
            # maxRot: Maximum roll, pitch, yaw rotational motion in
            # POSITIVE direction
            maxRot = max(data_rp[:, i])

        if min(data_rp[:, i]) < minRot:
            # minRot: Maximum roll, pitch, yaw rotational motion in
            # NEGATIVE direction
            minRot = min(data_rp[:, i])

    maxRotCheck = maxRot

    if abs(minRot) > maxRot:
        maxRotCheck = abs(minRot)

    if vox_size:
        # Mean x,y,z voxel dimension calculation.
        traLim = (vox_size[0] + vox_size[1] + vox_size[2]) * 1 / 3

        # maxRot for quality fixed to 2deg
        # maxTra(nslation) for quality fixed to
        # mean x,y,z voxel dim (traLim)
        if (maxTraCheck < traLim) and (maxRotCheck < 2):
            qc = True

    # Plot translation
    fig = plt.figure(figsize=figsize, facecolor="white")
    ax = fig.add_subplot(111)
    fig.subplots_adjust(
        left=None,
        bottom=None,
        right=None,
        top=None,
        wspace=None,
        hspace=None,
    )
    ax.set_title("Linear head motion parameters", fontsize=20, y=1.03)
    ax.set_xlabel("Dynamic scans", fontsize=14)
    ax.set_ylabel("Linear motion -X, Y, Z- (mm)", fontsize=14)
    # Plot using x_values for the x-axis
    ax.plot(x_values, data_rp[:, :3], label=("X", "Y", "Z"))
    ax.legend(loc="best")
    ax.set_xlim(0, xLim)
    #ax.set_ylim(minTra * 1.1, maxTra * 1.1)
    ax.set_ylim(-3, 3)
    ax.set_yticks([-3, -2, 0, 2, 3])
    ax.yaxis.grid(True, linestyle="-", which="major", color="grey", alpha=0.5)
    ax.xaxis.grid(True, linestyle="-", which="major", color="grey", alpha=0.5)
    ax.get_yaxis().set_tick_params(direction="out")
    ax.get_xaxis().set_tick_params(direction="out")
    for threshold in [-2, 2]:
        ax.axhline(
            threshold,
            color="red",
            linestyle="--",
            linewidth=1,
            alpha=0.7,
        )
    # High resolution: 2000px × 1118px.
    fig.savefig(out_file_tra, format="png", dpi=200)
    # Plot rotation
    ax.clear()
    ax.set_title("Rotational head motion parameters", fontsize=20, y=1.03)
    ax.set_xlabel("Dynamic scans", fontsize=14)
    ax.set_ylabel("Rotational motion -Roll, Pitch, Yaw- (°)", fontsize=14)
    ax.plot(x_values, data_rp[:, 3:], label=("Roll", "Pitch", "Yaw"))
    ax.legend(loc="best")
    ax.set_xlim(0, xLim)
    #ax.set_ylim(minRot * 1.1, maxRot * 1.1)
    ax.set_ylim(-3,3)
    ax.set_yticks([-3, -2, 0, 2, 3])
    ax.yaxis.grid(True, linestyle="-", which="major", color="grey", alpha=0.5)
    ax.xaxis.grid(True, linestyle="-", which="major", color="grey", alpha=0.5)
    for threshold in [-2, 2]:
        ax.axhline(
            threshold,
            color="red",
            linestyle="--",
            linewidth=1,
            alpha=0.7,
        )
    # High resolution: 2000px × 1118px.
    fig.savefig(out_file_rot, format="png", dpi=200)
    plt.close(fig)

    return qc