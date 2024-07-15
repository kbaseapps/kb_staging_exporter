/*
A KBase module: kb_staging_exporter
*/

module kb_staging_exporter {

  /* Ref to a WS object
      @id ws
  */
  typedef string WSRef;

  /* workspace name of the object
  */
  typedef string workspace_name;

  /* Input of the export_to_staging function
    input_ref: workspace object reference
    workspace_name: workspace name objects to be saved to 
    destination_dir: destination directory for downloaded files

    optional:
    generate_report: indicator for generating workspace report. (default False)
    export_genome: indicator for downloading Genbank (setting export_genome_genbank: 1) 
                                          or GFF (setting export_genome_gff: 1). (default download Genbank)
    export_alignment: indicator for downloading BAM (setting export_alignment_bam: 1) 
                                             or SAM (setting export_alignment_sam: 1). (default download BAM)
  */
  typedef structure {
    WSRef input_ref;
    workspace_name workspace_name;
    string destination_dir;
    string generate_report;
    mapping<string, string> export_genome;
    mapping<string, string> export_alignment;
  } ExportStagingParams;

  typedef structure {
      string report_name;
      string report_ref;
      string result_dir;
  } ExportStagingOutput;

  /* export_to_staging: export large file associated with workspace object to staging area*/
  funcdef export_to_staging (ExportStagingParams params) returns (ExportStagingOutput returnVal) authentication required;

  /* Input parameters for the export_json_to_staging function.
     
     input_ref - the workspace UPA of the object to download.
     destination_dir - the location in the staging area to store the compressed object data.
     format - the format of the data output. Currently supports:
         standard - The default. Saves the data as returned by the workspace.
         legacy_data_import_export - Saves the data in the same format as the old Data Import
             Export service.
  */
  typedef structure {
    WSRef input_ref;
    string destination_dir;
    string format;
  } ExportJSONParams;

  /* Result of the export_json_to_staging function.
     
     result_dir - the location in shared scratch space where the compressed object was stored.
     result_text - text describing the result of the app run suitable for displaying to a
         Narrative user.
  */
  typedef structure {
    string result_dir;
    string result_text;
  } ExportJSONResult;

  /* Download JSON object data for a workspace object and store it in zip file in the staging
     area.
  */
  funcdef export_json_to_staging(ExportJSONParams params) returns (ExportJSONResult ret)
      authentication required;
};
