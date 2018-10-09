import time
import os
import errno
import uuid
import shutil

from DataFileUtil.DataFileUtilClient import DataFileUtil
from KBaseReport.KBaseReportClient import KBaseReport
from ReadsUtils.ReadsUtilsClient import ReadsUtils
from AssemblyUtil.AssemblyUtilClient import AssemblyUtil
from GenomeFileUtil.GenomeFileUtilClient import GenomeFileUtil


def log(message, prefix_newline=False):
    time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()))
    print(('\n' if prefix_newline else '') + time_str + ': ' + message)


class staging_downloader:

    # staging file prefix
    STAGING_FILE_PREFIX = '/data/bulk/'

    def _mkdir_p(self, path):
        """
        _mkdir_p: make directory for given path
        """
        if not path:
            return
        try:
            os.makedirs(path)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise

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
        self._mkdir_p(result_dir)
        fwd = files['fwd']
        shutil.move(fwd, os.path.join(result_dir, os.path.basename(fwd)))
        rev = files.get('rev')
        if rev:
            shutil.move(rev, os.path.join(result_dir, os.path.basename(rev)))

        file_names = os.listdir(result_dir)
        for filename in file_names:
            new_file_name = reads_name + '_' + reads_ref.replace('/', '_') + \
                            '.' + filename.split('.', 1)[1]
            os.rename(os.path.join(result_dir, filename),
                      os.path.join(result_dir, new_file_name))

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
        self._mkdir_p(result_dir)
        shutil.move(download_ret.get('path'), result_dir)

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
        self._mkdir_p(result_dir)

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

    def __init__(self, config):
        self.ws_url = config["workspace-url"]
        self.callback_url = config['SDK_CALLBACK_URL']
        self.token = config['KB_AUTH_TOKEN']
        self.scratch = config['scratch']

        self.dfu = DataFileUtil(self.callback_url)
        self.ru = ReadsUtils(self.callback_url)
        self.au = AssemblyUtil(self.callback_url)
        self.gfu = GenomeFileUtil(self.callback_url)

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

        input_ref = params.get('input_ref')
        workspace_name = params.get('workspace_name')
        destination_dir = params.get('destination_dir')
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
            pass
        elif obj_type in ['KBaseGenomes.Genome']:
            result_dir = self._download_genome(input_ref, obj_name, params.get('export_genome'))
        else:
            raise ValueError('Unexpected data type')

        staging_dir = os.path.join(self.STAGING_FILE_PREFIX, ctx['user_id'], destination_dir)
        self._mkdir_p(staging_dir)
        files = os.listdir(result_dir)
        for file in files:
            shutil.copy2(os.path.join(result_dir, file), staging_dir)

        if not (set(os.listdir(staging_dir)) >= set(files)):
            raise ValueError('Unexpected error occurred during copying files')

        returnVal = dict()
        returnVal['result_dir'] = result_dir

        if generate_report:
            report_output = self._generate_export_report(files, obj_name, workspace_name)
            returnVal.update(report_output)

        return returnVal
