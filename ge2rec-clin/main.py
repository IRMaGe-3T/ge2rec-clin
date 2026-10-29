import json
import logging
import os
import shutil
import sys
import time
import re
from datetime import datetime
from bids import BIDSLayout
from PyQt5 import QtWidgets
from PyQt5.QtCore import QDir, QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QFileDialog, QMainWindow, QMessageBox
from PyQt5.uic import loadUi


from useful import check_file_ext, execute_command, copy_and_unzip_niigz
from logger import setup_logger
from bids_conversion import convert_to_bids
from preprocessing import run_preprocessing
from config_spm import configure_spm
from stats_spm import run_stats
from create_report import create_report
from params import get_acquisition_info

GE2REC_TASK = ["gene", "rappel", "reco"]
CLIN_TASK = ["langAud", "langVis", "mainD", "mainG", "levres", "piedD", "piedG", "clin", "handmotor"]

class ProcessingWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error_signal = pyqtSignal(str)
    log_signal = pyqtSignal(str) 

    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        #try:
        if 1==1:
            # Get all parameters
            dicom_directory = self.params["dicom_directory"]
            eprime_file = self.params["txt_file"]
            bids_sub = self.params["bids_sub"]
            bids_ses = self.params["bids_ses"]
            age = self.params["age"]
            sex = self.params["sex"]
            pathology = self.params["pathology"]
            lateralization = self.params["lateralization"]
            localization = self.params["localization"]
            hippo_sclerosis = self.params["hippo_sclerosis"]
            brain_surgery = self.params["brain_surgery"]
            neuropsych_assessment = self.params["neuropsych_assessment"]
            psychiatric_assessment = self.params["psychiatric_assessment"]
            dominant_hand = self.params["dominant_hand"]
            acquisition_type = self.params["acquisition_type"]
            dir_code_path = self.params["dir_code_path"]

            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            start = time.time()

            # Get config
            config_path = os.path.join(os.path.dirname(dir_code_path), "config")
            config_file = os.path.join(config_path, "config.json")
            with open(config_file, encoding="utf-8") as f:
                data = json.load(f)
            bids_config_file = data["BIDSConfigFile"]
            out_directory = data["OutputBIDSDirectory"]
            working_directory = data["WorkingDirectory"]
            spm_path = data["SPMPath"]

            self.progress.emit(5)

            # Create tmp directory
            working_directory_tmp = os.path.join(working_directory, "tmp_ge2rec-clin")
            os.makedirs(working_directory_tmp, exist_ok=True)

            if dicom_directory:
                valid_bool, in_ext, file_name = check_file_ext(dicom_directory, {"ZIP": "zip"})
                if not valid_bool:
                    raise Exception("DICOM directory is not a zip folder")
                cmd = ["unzip", dicom_directory, "-d", working_directory_tmp]
                dicom_directory_unzipped = os.path.join(working_directory_tmp, file_name)
                result, stderrl, sdtoutl = execute_command(cmd)
                while not os.path.exists(dicom_directory_unzipped):
                    time.sleep(1)

                # Conversion BIDS
                result, msg, info = convert_to_bids(dicom_directory_unzipped, bids_config_file, out_directory)
                if result == 0:
                    raise Exception(msg)
                patient_name = info["sub_name"]
                sess_name = info["sess_name"]

                # Copy DICOM 
                sourcedata_directory = os.path.join(out_directory, "sourcedata", f"sub-{patient_name}_ses-{sess_name}")
                if not os.path.exists(sourcedata_directory):
                    os.makedirs(sourcedata_directory)
                    shutil.copytree(dicom_directory_unzipped, os.path.join(sourcedata_directory, "DICOM"))
                    os.chdir(sourcedata_directory)
                    cmd = ["tar", "czvf", "DICOM.tar.gz", "DICOM"]
                    execute_command(cmd)
                    cmd = ["rm", "-rf", "DICOM"]
                    execute_command(cmd)
                shutil.rmtree(dicom_directory_unzipped)
            elif bids_sub != "N.A." and bids_ses != "N.A.":
                patient_name = bids_sub
                sess_name = bids_ses
            else:
                raise Exception("Select a DICOM directory or give BIDS subject/session")

            self.progress.emit(10)

            # Create work directories
            working_directory_tmp = os.path.join(working_directory_tmp, f"{patient_name}_{sess_name}_processing")
            os.makedirs(working_directory_tmp, exist_ok=True)
            derivatives_directory = os.path.join(out_directory, "derivatives", f"sub-{patient_name}", f"ses-{sess_name}")
            os.makedirs(derivatives_directory, exist_ok=True)

            # Logger
            logger = setup_logger(verbose=True, log_file=os.path.join(derivatives_directory, f"pipeline_GE2REC_{now}.log"))
            logger.info(f"Processing started: {now}")

            # SPM configuration
            configure_spm(spm_path)

            # Get anat and fmri files
            layout = BIDSLayout(out_directory)
            anat_file = layout.get(suffix="T1w", extension=[".nii", ".nii.gz"], subject=patient_name, session=sess_name)[0].path
            fmri_files = [i.path for i in layout.get(suffix="bold", extension=[".nii", ".nii.gz"], subject=patient_name, session=sess_name)]
            if len(fmri_files) == 0:
                raise Exception(f"No fMRI file")
            all_task = []
            events_files = []
            fmri_files_ge2rec = []
            fmri_files_clin = []
            for fmri_file in fmri_files:
                task = re.search(r"task-([^_]+)", fmri_file).group(1)
                if task not in all_task:
                   all_task.append(task)
                else:
                    if task not in ["clin"]:
                        raise Exception(f"Several files for task {task}")
                if task in GE2REC_TASK:
                    fmri_files_ge2rec.append(fmri_file)
                elif task in CLIN_TASK:
                    fmri_files_clin.append(fmri_file)
                
                events_file = fmri_file.replace("bold.nii.gz", "events.tsv").replace("bold.nii", "events.tsv")
                if not os.path.exists(events_file):
                    template = os.path.join(config_path, f"events_task-{task}_template.tsv")
                    shutil.copy2(template, events_file)
                events_files.append(events_file)
       
            self.progress.emit(20)

            # Subject info
            subject_info = {
                "subject": patient_name,
                "session": sess_name,
                "age": age,
                "sex": sex,
                "pathology": pathology,
                "lateralization_pathology": lateralization,
                "localization_pathology": localization,
                "hippo_sclerosis": hippo_sclerosis,
                "brain_surgery": brain_surgery,
                "neuropsych_assessment": neuropsych_assessment,
                "psychiatric_assessment": psychiatric_assessment,
                "dominant_hand": dominant_hand,
            }
            # GE2REC
            if fmri_files_ge2rec:
                # Copy files for preprocessing
                analysis_directory = os.path.join(derivatives_directory, "GE2REC")
                os.makedirs(analysis_directory, exist_ok=True)
                raw_directory = os.path.join(analysis_directory, "raw")
                unzip_anat_file_ge2rec = copy_and_unzip_niigz([anat_file], raw_directory)[0]
                unzip_fmri_files_ge2rec = copy_and_unzip_niigz(fmri_files_ge2rec, raw_directory)
                preproc_directory = os.path.join(analysis_directory, "spm_preprocessing")
                os.makedirs(preproc_directory, exist_ok=True)
                # Acquisition info
                acq_info = get_acquisition_info(unzip_fmri_files_ge2rec, unzip_anat_file_ge2rec)
                # Preprocessing
                #run_preprocessing(unzip_anat_file_ge2rec, unzip_fmri_files_ge2rec, preproc_directory, working_directory_tmp, acquisition_type, spm_path, acq_info, "ge2rec")
                self.progress.emit(50)
                # Stats
                #run_stats(unzip_fmri_files_ge2rec, analysis_directory, working_directory_tmp, acq_info)
                # Report
                create_report(analysis_directory, subject_info, acq_info, unzip_fmri_files_ge2rec, unzip_anat_file_ge2rec, "GE2REC-CLIN", eprime_file=eprime_file)
                shutil.rmtree(raw_directory)
            

            # CLINIQUE CLASSIC
            # if fmri_files_clin:
            #     self.progress.emit(75)
            #     analysis_directory_clin = os.path.join(derivatives_directory, "FONCTIONNELLE-CLIN")
            #     os.makedirs(analysis_directory_clin, exist_ok=True)
            #     raw_directory = os.path.join(analysis_directory_clin, "raw")
            #     unzip_anat_file_clin = copy_and_unzip_niigz([anat_file], raw_directory)[0]
            #     unzip_fmri_files_clin = copy_and_unzip_niigz(fmri_files_clin, raw_directory)
            #     preproc_directory_clin = os.path.join(analysis_directory_clin, "spm_preprocessing")
            #     os.makedirs(preproc_directory_clin, exist_ok=True)
            #     # Acquisition info
            #     acq_info_clin = get_acquisition_info(unzip_fmri_files_clin, unzip_anat_file_clin)
            #     # Preprocessing
            #     run_preprocessing(unzip_anat_file_clin, unzip_fmri_files_clin, preproc_directory_clin, working_directory_tmp, acquisition_type, spm_path, acq_info_clin, "clin")
            #     # Stats
            #     run_stats(unzip_fmri_files_clin, analysis_directory_clin, working_directory_tmp, acq_info_clin)
            #     # Report
            #     create_report(analysis_directory_clin, subject_info, acq_info_clin, unzip_fmri_files_clin, unzip_anat_file_clin, "FONCTIONNELLE-CLIN")
            #     shutil.rmtree(raw_directory)
            
           
            self.progress.emit(100)

            # Remove temp directory 
            shutil.rmtree(working_directory_tmp)

            end = time.time()
            total_time = (end - start) / 60
            logger.info(f"Processing finished in {total_time:.2f} minutes")
            self.finished.emit()

        # except Exception as e:
        #     self.error_signal.emit(str(e))

class App(QMainWindow):
    """
    Main windows Qt
    """

    def __init__(self):
        super(App, self).__init__()

        # Get ui
        self.dir_code_path = os.path.realpath(os.path.dirname(__file__))
        ui_file = os.path.join(self.dir_code_path, "interface.ui")
        loadUi(ui_file, self)

        # Connect signals and slots
        self.pushButton_browser.clicked.connect(self.browse_directory)
        self.pushButton_txt.clicked.connect(self.browse_txt_file)
        self.pushButton_run.clicked.connect(self.launch_processing)

        # Init variables
        self.dicom_directory = ""
        self.txt_file = ""

        self.reset_progress_bar()

    def reset_progress_bar(self):
        """Reset progress bar"""
        self.progressBar_run.setRange(0, 100)
        self.progressBar_run.setValue(0)
        self.progressBar_run.setStyleSheet(
            "QProgressBar::chunk { background-color: blue; }"
        )

    def browse_directory(self):
        """Browse DICOM directory"""

        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setViewMode(QFileDialog.List)
        file_dialog.setDirectory(QDir.homePath())
        file_dialog.setNameFilter("ZIP files (*.zip)")

        if file_dialog.exec_():
            if file_dialog.selectedFiles():
                self.dicom_directory = file_dialog.selectedFiles()[0]
                self.textEdit_output_browser.setText(self.dicom_directory)
                self.pushButton_run.setEnabled(True)
                self.reset_progress_bar()

    def browse_txt_file(self):
        """Browse TXT file"""

        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setViewMode(QFileDialog.List)
        file_dialog.setDirectory(QDir.homePath())
        file_dialog.setNameFilter("Text files (*.txt)")

        if file_dialog.exec_():
            if file_dialog.selectedFiles():
                self.txt_file = file_dialog.selectedFiles()[0]

                # Display selected file in the interface
                self.lineEdit_txt.setText(self.txt_file)

    def launch_processing(self):
        """Launch processing"""

        # Get params
        params = {
            "dicom_directory": self.dicom_directory,
            "txt_file": self.txt_file,
            "bids_sub": self.lineEdit_bids_sub.text().strip() or "N.A.",
            "bids_ses": self.lineEdit_bids_ses.text().strip() or "N.A.",
            "age": self.spinBox_age.value(),
            "sex": self.comboBox_sex.currentText(),
            "dominant_hand": self.comboBox_hand.currentText(),
            "pathology": self.comboBox_pathology.currentText(),
            "lateralization": self.comboBox_lat.currentText(),
            "localization": self.comboBox_localisation.currentText(),
            "hippo_sclerosis": self.comboBox_hippo.currentText(),
            "brain_surgery": self.comboBox_surgery.currentText(),
            "neuropsych_assessment": self.comboBox_neuropsy.currentText(),
            "psychiatric_assessment": self.comboBox_psy.currentText(),
            "acquisition_type": self.comboBox_acquistion_type.currentText(),
            "dir_code_path": self.dir_code_path
        }

        # Thread
        self.worker = ProcessingWorker(params)
        self.worker.progress.connect(self.progressBar_run.setValue)
        self.worker.finished.connect(self.on_processing_finished)
        self.worker.error_signal.connect(self.error)

        self.pushButton_run.setEnabled(False)

        # Launch thread
        self.worker.start()

    def on_processing_finished(self):
        self.pushButton_run.setEnabled(True)
        QMessageBox.information(self, "Info", "Processing done !")

    def error(self, message):
        """Error function"""
        print(f"Error during processing: {message}")

        self.progressBar_run.setStyleSheet(
            "QProgressBar::chunk { background-color: red; }"
        )

        self.show_error_message_box(str(message))

    def show_error_message_box(self, error_message):
        """Box with error message"""
        logging.error(error_message)

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Error")
        msg_box.setText("Error during processing:")
        msg_box.setDetailedText(error_message)
        msg_box.exec_()

    def show_confirmation_box(self, message):
        """Box to confirm an action"""
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("Confirmation")
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

        return msg_box.exec_()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    mainwindow = App()

    widget = QtWidgets.QStackedWidget()
    widget.addWidget(mainwindow)
    widget.show()

    sys.exit(app.exec_())