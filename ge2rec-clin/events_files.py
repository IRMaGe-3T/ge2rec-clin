import os
import shutil


def create_events_files_from_template(config_path, func_files):

    events_files = []

    for f in func_files:
        events_file= f.replace("nii.gz", "tsv").replace("nii", "tsv")
        events_files.append(events_file)
        if "gene" in f:
            template = os.path.join(config_path, "events_task-gene_template.tsv")
        elif "reco" in f:
            template  = os.path.join(config_path, "events_task-reco_template.tsv")
        elif "rappel" in f:
            template = os.path.join(config_path, "events_task-rappel_template.tsv")
        shutil.copy2(template, events_file)
    return events_files
