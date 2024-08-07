import time
import os
import datetime
import json
import errno
import uuid
import shutil
import stat
import gzip
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from installed_clients.GenomeFileUtilClient import GenomeFileUtil
from installed_clients.DataFileUtilClient import DataFileUtil
from installed_clients.AssemblyUtilClient import AssemblyUtil
from installed_clients.ReadsUtilsClient import ReadsUtils
from installed_clients.ReadsAlignmentUtilsClient import ReadsAlignmentUtils
from installed_clients.KBaseReportClient import KBaseReport
from installed_clients.sample_uploaderClient import sample_uploader
from installed_clients.KBaseDataObjectToFileUtilsClient import KBaseDataObjectToFileUtils
from installed_clients.WorkspaceClient import Workspace

def log(message, prefix_newline=False):
    time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()))
    print(('\n' if prefix_newline else '') + time_str + ': ' + message)


class staging_downloader:

    # staging file prefix
    STAGING_GLOBAL_FILE_PREFIX = '/data/bulk/'
    STAGING_USER_FILE_PREFIX = '/staging/'

    def _get_staging_file_prefix(self, token_user):
        """
        _get_staging_file_prefix: return staging area file path prefix

        directory pattern:
            preferred to return user specific path: /staging/
            if this path is not visible to user, use global bulk path: /data/bulk/user_name/
        """

        if os.path.exists(self.STAGING_USER_FILE_PREFIX):
            return self.STAGING_USER_FILE_PREFIX
        else:
            return os.path.join(self.STAGING_GLOBAL_FILE_PREFIX, token_user)

    def _validate_export_params(self, params):
        """
        validates params passed to export_to_staging
        """

        log('start validating export_to_staging params')

        # check for required parameters
        for p in ['input_ref', 'workspace_name', 'destination_dir']:
            if p not in params:
                raise ValueError('"{}" parameter is required, but missing'.format(p))

    def _generate_export_report(self, file_names, obj_name, workspace_name):
        log('start creating report')

        msg = 'Successfully exported object [{}] to staging area\n\n'.format(obj_name)
        msg += 'Exported files:\n' + '\n'.join(file_names)

        report_params = {'message': msg,
                         'workspace_name': workspace_name,
                         'report_object_name': 'staging_exporter_' + str(uuid.uuid4())}

        kbase_report_client = KBaseReport(self.callback_url, token=self.token)
        output = kbase_report_client.create_extended_report(report_params)

        report_output = {'report_name': output['name'], 'report_ref': output['ref']}

        return report_output

    def _download_reads(self, reads_ref, reads_name):
        """
        download Reads as FASTQ
        """

        log('start downloading Reads file')

        download_params = {'read_libraries': [reads_ref]}

        download_ret = self.ru.download_reads(download_params)
        files = download_ret['files'][reads_ref]['files']

        # create the output directory and move the file there
        result_dir = os.path.join(self.scratch, str(uuid.uuid4()))
        os.makedirs(result_dir, exist_ok=True)
        fwd = files['fwd']
        rev = files.get('rev')

        result_zip_name = reads_name + '_' + reads_ref.replace('/', '_') + '.FASTQ.zip'
        result_zip = os.path.join(result_dir, result_zip_name)

        with ZipFile(result_zip, 'w', ZIP_DEFLATED) as zipObj2:
            zipObj2.write(fwd, os.path.basename(fwd))
            if rev:
                zipObj2.write(rev, os.path.basename(rev))

        log('downloaded files:\n' + str(os.listdir(result_dir)))

        return result_dir

    def _download_assembly(self, assembly_ref, assembly_name):
        """
        download Assembly as FASTA
        """

        log('start downloading Assembly file')

        file_name = assembly_name + '_' + assembly_ref.replace('/', '_') + '.fa'

        download_params = {'ref': assembly_ref, 'filename': file_name}
        download_ret = self.au.get_assembly_as_fasta(download_params)

        # create the output directory and move the file there
        result_dir = os.path.join(self.scratch, str(uuid.uuid4()))
        os.makedirs(result_dir, exist_ok=True)
        shutil.move(download_ret.get('path'), result_dir)

        log('downloaded files:\n' + str(os.listdir(result_dir)))

        return result_dir

    def _download_alignment(self, alignment_ref, alignment_name, export_alignment):
        """
        downloand Alignment as BAM or SAM
        """
        log('start downloading Alignment file')

        if not export_alignment:
            log('start downloading BAM as default')
            export_alignment = {'export_alignment_bam': 1}

        # create the output directory and move the file there
        result_dir = os.path.join(self.scratch, str(uuid.uuid4()))
        os.makedirs(result_dir, exist_ok=True)

        if export_alignment.get('export_alignment_bam'):
            download_params = {'source_ref': alignment_ref,
                               'downloadBAI': True}
            download_ret = self.rau.download_alignment(download_params)

            destination_dir = download_ret.get('destination_dir')

            file_names = os.listdir(destination_dir)
            for filename in file_names:
                new_file_name = alignment_name + '_' + alignment_ref.replace('/', '_') + \
                                '.' + filename.split('.', 1)[1]
                os.rename(os.path.join(destination_dir, filename),
                          os.path.join(destination_dir, new_file_name))

                shutil.copy2(os.path.join(destination_dir, new_file_name), result_dir)

        if export_alignment.get('export_alignment_sam'):
            download_params = {'source_ref': alignment_ref,
                               'downloadBAI': True,
                               'downloadSAM': True}
            download_ret = self.rau.download_alignment(download_params)

            destination_dir = download_ret.get('destination_dir')

            file_names = os.listdir(destination_dir)
            for filename in file_names:
                new_file_name = alignment_name + '_' + alignment_ref.replace('/', '_') + \
                                '.' + filename.split('.', 1)[1]
                os.rename(os.path.join(destination_dir, filename),
                          os.path.join(destination_dir, new_file_name))

                shutil.copy2(os.path.join(destination_dir, new_file_name), result_dir)

        log('downloaded files:\n' + str(os.listdir(result_dir)))

        return result_dir

    def _download_metagenome(self, metagenome_ref, metagenome_name):
        """
        """
        log("start downloading Annotated Metagenome Assembly files")
        result_dir = os.path.join(self.scratch, str(uuid.uuid4()))
        os.makedirs(result_dir, exist_ok=True)
        # download gff file
        download_ret = self.gfu.metagenome_to_gff({'metagenome_ref': metagenome_ref})
        gff_file = download_ret.get('file_path')
        gff_file_name = os.path.basename(gff_file)
        shutil.move(gff_file, result_dir)

        file_name_prefix = str(metagenome_name).replace(' ', '_') + '_' + metagenome_ref.replace('/', '_')
        new_gff_file_name = file_name_prefix + os.path.splitext(gff_file_name)[1]

        os.rename(os.path.join(result_dir, gff_file_name),
                  os.path.join(result_dir, new_gff_file_name))

        prot_params = {
            'ama_ref': metagenome_ref,
            'file': file_name_prefix +'_prot.fasta',
            'dir': result_dir,
            'console': [],
            'invalid_msgs': [],
            'residue_type': "prot",
            'feature_type': "ALL",
            'record_id_pattern': '%%feature_id%%',
            'record_desc_pattern': '[%%genome_id%%]',
            'case': 'upper',
            'linewrap': 50
        }
        prot_fp = self.dotfu.AnnotatedMetagenomeAssemblyToFASTA(prot_params)['fasta_file_path']
        nucl_params = {
            'ama_ref': metagenome_ref,
            'file': file_name_prefix +'_gene_nuc.fna',
            'dir': result_dir,
            'console': [],
            'invalid_msgs': [],
            'residue_type': "nucl",
            'feature_type': "ALL",
            'record_id_pattern': '%%feature_id%%',
            'record_desc_pattern': '[%%genome_id%%]',
            'case': 'upper',
            'linewrap': 50
        }
        nucl_fp = self.dotfu.AnnotatedMetagenomeAssemblyToFASTA(nucl_params)['fasta_file_path']
        # gzip files here.
        ret = self.au.get_fastas({'ref_lst': [metagenome_ref]})
        fasta_fp = ret[metagenome_ref]['paths'][0]
        shutil.move(fasta_fp, result_dir)

        fasta_file_name = os.path.basename(fasta_fp)
        new_fasta_file_name = file_name_prefix + os.path.splitext(fasta_file_name)[1]
        new_fasta_file_path = os.path.join(result_dir, new_fasta_file_name)
        os.rename(os.path.join(result_dir, fasta_file_name),
                  new_fasta_file_path)

        for fp in [prot_fp, nucl_fp, new_fasta_file_path]:
            with open(fp, 'rb') as f_in:
                with gzip.open(fp + '.gz', 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            # remove non-gzipped versions
            os.remove(fp)

        log('downloaded files:\n' + str(os.listdir(result_dir)))

        return result_dir

    def _download_sampleset(self, sample_set_ref, sample_set_name):
        """
        downloand SampleSet in SESAR format
        """
        log('start downloading SampleSet in SESAR format')

        # create the output directory and move the file there
        result_dir = os.path.join(self.scratch, str(uuid.uuid4()))
        os.makedirs(result_dir, exist_ok=True)

        params = {
            "input_ref": sample_set_ref,
            "file_format": "SESAR"
        }
        download_ret = self.sp_uploader.export_samples(params)

        files = os.listdir(download_ret.get('result_dir'))
        for file in files:
            if file.endswith('.csv'):
                shutil.copy2(os.path.join(download_ret.get('result_dir'), file),
                             result_dir)

        log('downloaded files:\n' + str(os.listdir(result_dir)))

        return result_dir

    def _download_genome(self, genome_ref, genome_name, export_genome):
        """
        download Genome as GENBANK or GFF
        """

        log('start downloading Genome file')

        if not export_genome:
            log('start downloading GENBANK as default')
            export_genome = {'export_genome_genbank': 1}

        # create the output directory and move the file there
        result_dir = os.path.join(self.scratch, str(uuid.uuid4()))
        os.makedirs(result_dir, exist_ok=True)

        if export_genome.get('export_genome_genbank'):
            download_params = {'genome_ref': genome_ref}
            download_ret = self.gfu.genome_to_genbank(download_params)

            genbank_file = download_ret.get('genbank_file').get('file_path')
            genbank_file_name = os.path.basename(genbank_file)
            shutil.move(genbank_file, result_dir)

            new_file_name = genome_name + '_' + genome_ref.replace('/', '_') + \
                '.' + genbank_file_name.split('.', 1)[1]

            os.rename(os.path.join(result_dir, genbank_file_name),
                      os.path.join(result_dir, new_file_name))

        if export_genome.get('export_genome_gff'):
            download_params = {'genome_ref': genome_ref}
            download_ret = self.gfu.genome_to_gff(download_params)

            gff_file = download_ret.get('file_path')
            gff_file_name = os.path.basename(gff_file)
            shutil.move(gff_file, result_dir)

            new_file_name = genome_name + '_' + genome_ref.replace('/', '_') + \
                '.' + gff_file_name.split('.', 1)[1]

            os.rename(os.path.join(result_dir, gff_file_name),
                      os.path.join(result_dir, new_file_name))

        log('downloaded files:\n' + str(os.listdir(result_dir)))

        return result_dir

    def _recursive_chmod(self, path, bitmask):
        for dirpath, _, filenames in os.walk(path):
            os.chmod(dirpath, bitmask)
            for filename in filenames:
                os.chmod(os.path.join(dirpath, filename), bitmask)

    def __init__(self, config):
        self.ws_url = config["workspace-url"]
        self.callback_url = config['SDK_CALLBACK_URL']
        self.token = config['KB_AUTH_TOKEN']
        self.scratch = config['scratch']

        self.ws = Workspace(self.ws_url, token=self.token)
        self.dfu = DataFileUtil(self.callback_url)
        self.ru = ReadsUtils(self.callback_url)
        self.au = AssemblyUtil(self.callback_url)
        self.gfu = GenomeFileUtil(self.callback_url)
        self.rau = ReadsAlignmentUtils(self.callback_url)
        self.sp_uploader = sample_uploader(self.callback_url, service_ver='beta')
        self.dotfu = KBaseDataObjectToFileUtils(self.callback_url, token=self.token)

    def export_to_staging(self, ctx, params):
        """
        export large file associated with workspace object to staging area

        params:
        input_ref: workspace object reference
        workspace_name: workspace name objects to be saved to
        destination_dir: destination directory for downloaded files

        optional:
        generate_report: indicator for generating workspace report. (default False)
        """

        self._validate_export_params(params)

        input_ref = params['input_ref']
        workspace_name = params['workspace_name']
        destination_dir = self._norm_dest_dir(params['destination_dir'])
        generate_report = params.get('generate_report', False)

        obj_source = self.dfu.get_objects({"object_refs": [input_ref]})['data'][0]

        obj_info = obj_source.get('info')
        obj_type = obj_info[2].split('-')[0]
        obj_name = obj_info[1]

        if obj_type in ['KBaseFile.PairedEndLibrary', 'KBaseFile.SingleEndLibrary']:
            result_dir = self._download_reads(input_ref, obj_name)
        elif obj_type in ['KBaseGenomeAnnotations.Assembly']:
            result_dir = self._download_assembly(input_ref, obj_name)
        elif obj_type in ['KBaseRNASeq.RNASeqAlignment']:
            result_dir = self._download_alignment(input_ref, obj_name, params.get('export_alignment'))
        elif obj_type in ['KBaseGenomes.Genome']:
            result_dir = self._download_genome(input_ref, obj_name, params.get('export_genome'))
        elif obj_type in ['KBaseMetagenomes.AnnotatedMetagenomeAssembly']:
            result_dir = self._download_metagenome(input_ref, obj_name)
        elif obj_type in ['KBaseSets.SampleSet']:
            result_dir = self._download_sampleset(input_ref, obj_name)
        else:
            raise ValueError('Unexpected data type')

        files = self._move_results_to_staging(ctx, destination_dir, result_dir)

        returnVal = dict()
        returnVal['result_dir'] = result_dir

        if generate_report:
            report_output = self._generate_export_report(files, obj_name, workspace_name)
            returnVal.update(report_output)

        return returnVal
    
    def _norm_dest_dir(self, destination_dir):
        dd = os.path.normpath(destination_dir)
        if dd.startswith(".."):
            raise ValueError(
                "destination_dir may not point to an area outside of the user's staging area")
        return dd
    
    def _move_results_to_staging(self, ctx, destination_dir, result_dir):
        staging_dir_prefix = self._get_staging_file_prefix(ctx['user_id'])
        staging_dir = os.path.join(staging_dir_prefix, destination_dir)
        os.makedirs(staging_dir, exist_ok=True)
        files = os.listdir(result_dir)
        for file in files:
            # Doesn't use move to keep result dir around for other apps that might not
            # have access to the staging area
            shutil.copy2(os.path.join(result_dir, file), staging_dir)

        # This is a KBase specific hack to allow the staging service to delete the files and
        # folders written by this module. Currently the staging service runs as user 800 and
        # this module runs as root (bleah) so the staging service throws an error if the user
        # tries to delete the folder. The staging service belongs to the root group, however,
        # so if we add write privs to the root group that solves the issue.
        # Longer term this app should not run as root and should chown ownership to the staging
        # service when it has a static user name vs. a number that might change.
        basemode = os.stat(staging_dir).st_mode
        self._recursive_chmod(staging_dir, basemode | stat.S_IWGRP)
        
        if not (set(os.listdir(staging_dir)) >= set(files)):
            raise ValueError('Unexpected error occurred during copying files')
        return files

    def export_json_to_staging(self, ctx, params):
        for p in ['input_ref', 'destination_dir']:
            if p not in params:
                raise ValueError('"{}" parameter is required, but missing'.format(p))
        format = params.get("format")
        if format == None or format.strip() == "":
            format = "standard"
        else:
            format = format.strip()
        if format not in ["standard", "legacy_data_import_export"]:
            raise ValueError("Unknown format: " + format)
        destination_dir = self._norm_dest_dir(params['destination_dir'])
        # can't use DFU because it doesn't include provenance
        obj = self.ws.get_objects2({"objects": [{"ref": params["input_ref"]}]})['data'][0]
        cleanname = obj["info"][1].replace("|", "_")
        result_dir = Path(self.scratch, str(uuid.uuid4()))
        os.makedirs(result_dir, exist_ok=True)
        if format == "legacy_data_import_export":
            prov = {
                "info": obj["info"],
                "provenance": {
                    "copy_source_inaccessible": obj["copy_source_inaccessible"],
                    "created": obj["created"],
                    "creator": obj["creator"],
                    "extracted_ids": obj["extracted_ids"],
                    "info": obj["info"],  # match legacy output even though it's redundant
                    "provenance": obj["provenance"],
                    "refs": obj["refs"]
                }
            }
            datestr = datetime.datetime.now().isoformat().replace(":", "").replace(".", "")
            writeobjs = {
                cleanname + ".json": obj["data"],
                "KBase_object_details_" + cleanname + datestr + ".json": prov,
            }
        else:
            writeobjs = {cleanname + ".json": obj}
        zipfile = cleanname + ".json.zip"
        with ZipFile(result_dir / zipfile, 'w', ZIP_DEFLATED) as z:
            for fn, o in writeobjs.items():
                z.writestr(fn, json.dumps(o, indent=4))
        self._move_results_to_staging(ctx, destination_dir, result_dir)
        return {
            "result_dir": str(result_dir),
            "result_text": "Successfully exported JSON to staging area in file "
                + os.path.join(destination_dir, zipfile)
        }
