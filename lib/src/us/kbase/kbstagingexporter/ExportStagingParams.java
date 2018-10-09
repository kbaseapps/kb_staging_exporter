
package us.kbase.kbstagingexporter;

import java.util.HashMap;
import java.util.Map;
import javax.annotation.Generated;
import com.fasterxml.jackson.annotation.JsonAnyGetter;
import com.fasterxml.jackson.annotation.JsonAnySetter;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;


/**
 * <p>Original spec-file type: ExportStagingParams</p>
 * <pre>
 * Input of the export_to_staging function
 * input_ref: workspace object reference
 * workspace_name: workspace name objects to be saved to 
 * destination_dir: destination directory for downloaded files
 * optional:
 * generate_report: indicator for generating workspace report. (default False)
 * export_genome: indicator for downloading Genbank (setting export_genome_genbank: 1) 
 *                                       or GFF (setting export_genome_gff: 1). (default download Genbank)
 * export_alignment: indicator for downloading BAM (setting export_alignment_bam: 1) 
 *                                          or SAM (setting export_alignment_sam: 1). (default download BAM)
 * </pre>
 * 
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@Generated("com.googlecode.jsonschema2pojo")
@JsonPropertyOrder({
    "input_ref",
    "workspace_name",
    "destination_dir",
    "generate_report",
    "export_genome",
    "export_alignment"
})
public class ExportStagingParams {

    @JsonProperty("input_ref")
    private java.lang.String inputRef;
    @JsonProperty("workspace_name")
    private java.lang.String workspaceName;
    @JsonProperty("destination_dir")
    private java.lang.String destinationDir;
    @JsonProperty("generate_report")
    private java.lang.String generateReport;
    @JsonProperty("export_genome")
    private Map<String, String> exportGenome;
    @JsonProperty("export_alignment")
    private Map<String, String> exportAlignment;
    private Map<java.lang.String, Object> additionalProperties = new HashMap<java.lang.String, Object>();

    @JsonProperty("input_ref")
    public java.lang.String getInputRef() {
        return inputRef;
    }

    @JsonProperty("input_ref")
    public void setInputRef(java.lang.String inputRef) {
        this.inputRef = inputRef;
    }

    public ExportStagingParams withInputRef(java.lang.String inputRef) {
        this.inputRef = inputRef;
        return this;
    }

    @JsonProperty("workspace_name")
    public java.lang.String getWorkspaceName() {
        return workspaceName;
    }

    @JsonProperty("workspace_name")
    public void setWorkspaceName(java.lang.String workspaceName) {
        this.workspaceName = workspaceName;
    }

    public ExportStagingParams withWorkspaceName(java.lang.String workspaceName) {
        this.workspaceName = workspaceName;
        return this;
    }

    @JsonProperty("destination_dir")
    public java.lang.String getDestinationDir() {
        return destinationDir;
    }

    @JsonProperty("destination_dir")
    public void setDestinationDir(java.lang.String destinationDir) {
        this.destinationDir = destinationDir;
    }

    public ExportStagingParams withDestinationDir(java.lang.String destinationDir) {
        this.destinationDir = destinationDir;
        return this;
    }

    @JsonProperty("generate_report")
    public java.lang.String getGenerateReport() {
        return generateReport;
    }

    @JsonProperty("generate_report")
    public void setGenerateReport(java.lang.String generateReport) {
        this.generateReport = generateReport;
    }

    public ExportStagingParams withGenerateReport(java.lang.String generateReport) {
        this.generateReport = generateReport;
        return this;
    }

    @JsonProperty("export_genome")
    public Map<String, String> getExportGenome() {
        return exportGenome;
    }

    @JsonProperty("export_genome")
    public void setExportGenome(Map<String, String> exportGenome) {
        this.exportGenome = exportGenome;
    }

    public ExportStagingParams withExportGenome(Map<String, String> exportGenome) {
        this.exportGenome = exportGenome;
        return this;
    }

    @JsonProperty("export_alignment")
    public Map<String, String> getExportAlignment() {
        return exportAlignment;
    }

    @JsonProperty("export_alignment")
    public void setExportAlignment(Map<String, String> exportAlignment) {
        this.exportAlignment = exportAlignment;
    }

    public ExportStagingParams withExportAlignment(Map<String, String> exportAlignment) {
        this.exportAlignment = exportAlignment;
        return this;
    }

    @JsonAnyGetter
    public Map<java.lang.String, Object> getAdditionalProperties() {
        return this.additionalProperties;
    }

    @JsonAnySetter
    public void setAdditionalProperties(java.lang.String name, Object value) {
        this.additionalProperties.put(name, value);
    }

    @Override
    public java.lang.String toString() {
        return ((((((((((((((("ExportStagingParams"+" [inputRef=")+ inputRef)+", workspaceName=")+ workspaceName)+", destinationDir=")+ destinationDir)+", generateReport=")+ generateReport)+", exportGenome=")+ exportGenome)+", exportAlignment=")+ exportAlignment)+", additionalProperties=")+ additionalProperties)+"]");
    }

}
