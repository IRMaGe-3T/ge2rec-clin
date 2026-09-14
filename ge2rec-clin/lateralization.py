import os
import nibabel as nib
import numpy as np
import scipy.ndimage as nd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from nilearn.image import resample_to_img



def lateralization_index_iter_curves(
    in_file, mask, mask_right, mask_left, roi_name, out_png
):
    """
    Function to iteratively calculate lateralization indices.
    Partial python adaptation of the LI-toolbox
    (https://www.fil.ion.ucl.ac.uk/spm/ext/#LI)
    (LI_iter.m)

     If you are using this function cite:
    - Wilke M & Lidzba K: LI-tool: A new toolbox to assess
    lateralization in functional MR-data, J Neurosci Meth, 2007, 163: 128-136

    :param string that represents a path in_file: SPMT filepath
    :param string that represents a path mask: main inclusive mask filepath
    :param string that represents a path mask_left: mask left filepath
    :param string that represents a path mask_right: mask right filepath
    :param string roi_name: main inclusive mask name
    :param string that represents a out_png: out path

    """
    vol_data = np.asarray(nib.load(in_file).dataobj)
    vol_mask_img = nib.load(mask)
    vol_mask = np.asarray(vol_mask_img.dataobj)
    vol_mask_right = np.asarray(nib.load(mask_right).dataobj)
    vol_mask_left = np.asarray(nib.load(mask_left).dataobj)

    if (
        (vol_mask.shape[0] != vol_data.shape[0])
        or (vol_mask.shape[1] != vol_data.shape[1])
        or (vol_mask.shape[2] != vol_data.shape[2])
    ):
        # Resample volume
        new_data = resample_to_img(in_file, mask, interpolation="linear")
        vol_data_new = new_data.dataobj
        # new_img = nib.Nifti1Image(
        #     vol_data_new,
        #     vol_mask_img.affine,
        #     vol_mask_img.header
        # )
        # out = in_file.replace(".nii", f"_{mask.split('/')[-1].replace(".nii","")}_resampled.nii")
        # nib.save(new_img, out)
    else:
        vol_data_new = vol_data

    iteration = 20
    mx = 0
    min_cluster_size = 5
    min_nb_voxel = 5

    # Compute mask weighting factor
    # (represent the relation of the volumes of the masks)
    mwf = np.sum((vol_mask_left > 0.1) * (vol_mask > 0.1)) / np.sum(
        (vol_mask_right > 0.1) * (vol_mask > 0.1)
    )

    indexes = []
    thresholds = []
    number_voxels_right = []
    number_voxels_left = []

    for j in range(1, iteration + 1):
        # Get threshold
        if j == 1:
            thr = 0
        else:
            thr = (j - 1) * mx / iteration

        vol_data_thr = np.where(vol_data_new > thr, vol_data_new, 0)
        res_left = vol_data_thr * (vol_mask > 0.1) * (vol_mask_left > 0.1)
        res_right = vol_data_thr * (vol_mask > 0.1) * (vol_mask_right > 0.1)
        if j == 1:
            # Update max voxel value in masked input image to get threshold
            mx = np.max(res_left + res_right)

        # Labelling
        labels_right, num_right = nd.label(res_right)
        labels_left, num_left = nd.label(res_left)
        labels_right = np.sort(labels_right.ravel())
        labels_right = labels_right[labels_right != 0]
        labels_left = np.sort(labels_left.ravel())
        labels_left = labels_left[labels_left != 0]

        # Get number of voxels decision is based on
        nvoxr = labels_right.size
        nvoxl = labels_left.size
        if nvoxl < min_nb_voxel or nvoxr < min_nb_voxel:
            # print(
            #     f"WARNING, number of voxel for threshold {thr} "
            #     "is below the required minimum, abort iteration"
            # )
            break
        # Check if there is at least one cluster > min_cluster_size
        cluster_left = 0
        cluster_right = 0
        for i in range(1, num_right + 1):
            cluster = np.where(labels_right == i, labels_right, 0)
            if np.sum(cluster) > min_cluster_size:
                cluster_right = 1
            if cluster_right == 1:
                # only need one cluster
                break
        for i in range(1, num_left + 1):
            cluster = np.where(labels_left == i, labels_left, 0)
            if np.sum(cluster) > min_cluster_size:
                cluster_left = 1
            if cluster_left == 1:
                # only need one cluster
                break
        if cluster_left == 0 or cluster_right == 0:
            print(
                f"WARNING, cluster size for threshold {thr} "
                "is below the required minimum, abort iteration"
            )
            break

        # Compute Lateralization index
        activation_left = np.sum(res_left)
        activation_right = np.sum(res_right)

        lateralization_index = (activation_left / mwf - activation_right) / (
            activation_left / mwf + activation_right
        )
        thresholds.append(round(thr, 4))
        indexes.append(round(lateralization_index, 4))
        number_voxels_right.append(nvoxr)
        number_voxels_left.append(nvoxl)

    # Plot LI
    fig = plt.figure(figsize=(12, 5.6), facecolor="white")
    ax = fig.add_subplot(111)
    fig.subplots_adjust(
        left=None,
        bottom=None,
        right=None,
        top=None,
        wspace=None,
        hspace=None,
    )
    ax.set_title(f"Lateralization index {roi_name}", fontsize=20, y=1.03)
    ax.set_xlabel("Threshold", fontsize=14)
    ax.set_ylabel("Lateralization Index", fontsize=14)
    ax.plot(thresholds, indexes, color="black")
    ax.set_xlim(0, max(thresholds))
    ax.set_ylim(-1, 1)
    ax2 = ax.twinx()
    y_1 = np.linspace(-100, -40, len(thresholds))
    ax2.scatter(thresholds, y_1, s=1, color="blue")
    for i, txt in enumerate(number_voxels_right):
        ax2.annotate(str(txt), (thresholds[i], y_1[i]))
    y_2 = np.linspace(100, 40, len(thresholds))
    ax2.scatter(thresholds, y_2, s=1, color="red")
    for i, txt in enumerate(number_voxels_left):
        ax2.annotate(str(txt), (thresholds[i], y_2[i]))
    ax2.set_axis_off()
    ax.yaxis.grid(True, linestyle="-", which="major", color="grey", alpha=0.5)
    ax.xaxis.grid(True, linestyle="-", which="major", color="grey", alpha=0.5)
    ax.fill_between(thresholds, -0.2, 0.2, facecolor="lightgreen", alpha=0.5)
    ax.fill_between(thresholds, 0.2, 1, facecolor="lightcoral", alpha=0.5)
    ax.fill_between(thresholds, -0.2, -1, facecolor="lightblue", alpha=0.5)
    ax.annotate(
        "right hemispheric dominance", (0.2, -0.6), color="blue", fontsize=12
    )
    ax.annotate(
        "left hemispheric dominance", (0.2, 0.6), color="red", fontsize=12
    )
    ax.annotate(
        "bilateral representation", (0.2, 0.0), color="green", fontsize=12
    )
    ax.annotate("# of voxels (L)", (max(thresholds) - 1, 0.6), color="red")
    ax.annotate("# of voxels (R)", (max(thresholds) - 1, -0.6), color="blue")
    ax.get_yaxis().set_tick_params(direction="out")
    ax.get_xaxis().set_tick_params(direction="out")
    plt.savefig(out_png, bbox_inches="tight")
    plt.close(fig)


def get_lateralization_curves(spmT_file, out_dir):

    out_dir_LI = os.path.join(out_dir, "LI-toolbox")
    os.makedirs(out_dir_LI, exist_ok=True)
    name = os.path.dirname(spmT_file).split('/')[-1] + "_" + os.path.basename(spmT_file).split('.')[0]
    out_png_images = {}
    sources_rois_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "ROIs"
        )
 
    mask_right = os.path.join(sources_rois_dir, "LI-toolbox", "LI-right.nii")
    mask_left = os.path.join(sources_rois_dir, "LI-toolbox", "LI-left.nii")
    rois = {
        "temporal": os.path.join(sources_rois_dir, "LI-toolbox", "LI-temporal-mask.nii"), 
        "frontal" : os.path.join(sources_rois_dir, "LI-toolbox", "LI-frontal-mask.nii"),
        "middle_frontal_gyrus": os.path.join(sources_rois_dir, "HardvardOxford", "HarvardOxford-cort-maxprob-thr25-2mm_3.nii"),
        "inferior_frontal_gyrus_triangularis": os.path.join(sources_rois_dir, "HardvardOxford", "HarvardOxford-cort-maxprob-thr25-2mm_4.nii"),
        "inferior_frontal_gyrus_opercularis": os.path.join(sources_rois_dir, "HardvardOxford", "HarvardOxford-cort-maxprob-thr25-2mm_5.nii"),
        "superior_temporal_gyrus_anterior": os.path.join(sources_rois_dir, "HardvardOxford", "HarvardOxford-cort-maxprob-thr25-2mm_8.nii"),
        "superior_temporal_gyrus_posterior": os.path.join(sources_rois_dir, "HardvardOxford", "HarvardOxford-cort-maxprob-thr25-2mm_9.nii"),
        "middle_temporal_gyrus_temporooccipital": os.path.join(sources_rois_dir, "HardvardOxford", "HarvardOxford-cort-maxprob-thr25-2mm_12.nii"),
        "inferior_temporal_gyrus_anterior": os.path.join(sources_rois_dir, "HardvardOxford", "HarvardOxford-cort-maxprob-thr25-2mm_13.nii"),
        "inferior_tempotal_gyrus_posterior": os.path.join(sources_rois_dir, "HardvardOxford", "HarvardOxford-cort-maxprob-thr25-2mm_14.nii")
    }

    for roi in list(rois.keys()):
        mask = rois[roi]
        out_png = os.path.join(out_dir_LI, f"{name}_LI_{roi}.png")
        out_png_images[roi] = out_png
        lateralization_index_iter_curves(
            spmT_file, mask, mask_right, mask_left, roi, out_png
        )
    return out_png_images
