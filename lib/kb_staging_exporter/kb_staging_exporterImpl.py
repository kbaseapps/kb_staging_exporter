# -*- coding: utf-8 -*-
#BEGIN_HEADER
import os

from kb_staging_exporter.Utils.staging_downloader import staging_downloader
#END_HEADER


class kb_staging_exporter:
    '''
    Module Name:
    kb_staging_exporter

    Module Description:
    A KBase module: kb_staging_exporter
    '''

    ######## WARNING FOR GEVENT USERS ####### noqa
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    ######################################### noqa
    VERSION = "1.0.4"
    GIT_URL = "https://github.com/Tianhao-Gu/kb_staging_exporter.git"
    GIT_COMMIT_HASH = "0c99bcad448817fa9b29b998cf8c099686be675d"

    #BEGIN_CLASS_HEADER
    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.config = config
        self.config['SDK_CALLBACK_URL'] = os.environ['SDK_CALLBACK_URL']
        self.config['KB_AUTH_TOKEN'] = os.environ['KB_AUTH_TOKEN']
        self.scratch = config['scratch']
        self.staging_downloader = staging_downloader(self.config)
        #END_CONSTRUCTOR
        pass


    def export_to_staging(self, ctx, params):
        """
        export_to_staging: export large file associated with workspace object to staging area
        :param params: instance of type "ExportStagingParams" (Input of the
           export_to_staging function input_ref: workspace object reference
           workspace_name: workspace name objects to be saved to
           destination_dir: destination directory for downloaded files
           optional: generate_report: indicator for generating workspace
           report. (default False) export_genome: indicator for downloading
           Genbank (setting export_genome_genbank: 1) or GFF (setting
           export_genome_gff: 1). (default download Genbank)
           export_alignment: indicator for downloading BAM (setting
           export_alignment_bam: 1) or SAM (setting export_alignment_sam: 1).
           (default download BAM)) -> structure: parameter "input_ref" of
           type "WSRef" (Ref to a WS object @id ws), parameter
           "workspace_name" of type "workspace_name" (workspace name of the
           object), parameter "destination_dir" of String, parameter
           "generate_report" of String, parameter "export_genome" of mapping
           from String to String, parameter "export_alignment" of mapping
           from String to String
        :returns: instance of type "ExportStagingOutput" -> structure:
           parameter "report_name" of String, parameter "report_ref" of
           String, parameter "result_dir" of String
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN export_to_staging
        returnVal = self.staging_downloader.export_to_staging(ctx, params)
        #END export_to_staging

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method export_to_staging return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]
    def status(self, ctx):
        #BEGIN_STATUS
        returnVal = {'state': "OK",
                     'message': "",
                     'version': self.VERSION,
                     'git_url': self.GIT_URL,
                     'git_commit_hash': self.GIT_COMMIT_HASH}
        #END_STATUS
        return [returnVal]
