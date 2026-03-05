# ui_record_panel.py

RECORD_PANEL = """<div class=\"panel panel-record\">
    <div class=\"panel-title\">Recording Control</div>

    
    <div class=\"panel-body\">
        <div class=\"btn-row\">
        <button id=\"recordToggleBtn\" class=\"btn-record-off\" onclick=\"toggleRecord()\">
        Toggle Rec
        </button>
	    <button id=\"recordDownloadBtn\" onclick=\"downloadSelectedRecording()\">Download ZIP</button>
	    <button id=\"recordDeleteBtn\" class=\"btn-danger\" onclick=\"deleteSelectedRecording()\">Delete</button>
	</div>

    <select id=\"recordSessionSelect\" aria-label=\"Select recording session\"></select>

    <div id=\"recordStatusText\" class=\"record-status-text\">
        <span class=\"rec-dot rec-dot-off\"></span>
        Recording
    </div>
    </div>
</div>
"""