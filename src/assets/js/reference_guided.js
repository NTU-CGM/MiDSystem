upload_files_stat={"R1":false, "R2":false, "ref":false};
confirmed_urls_stat={"reads":false, "ref":false};
var ajaxcounter=0;
$(document).ready(function () {
    $("table").hide(); 
    $("#augustus").hide();
    $("#upload_button").hide();
    $("#reads_url_upload").hide();
    $("#ref_url_upload").hide();
    $("#fin_upload").hide();
    $("#ref_upload").hide();
    //$("table[name='pred_assm_table']").show();
    //$.fn.zTree.init($("#treeDemo"), setting, zNodes);
    /*
    var $select = $('#demo');
      for (var ii = 0; ii < 2000; ++ii) {
        var $option = $('<option value="fruit' + ii +'" data-section="Smoothies/' + ii + '" data-description="The greatest flavor">Passion Fruit</option>');
        $select.append($option);
      }*/
    //please see https://github.com/patosai/tree-multiselect.js
    /*
    function treeOnChange(allSelectedItems, addedItems, removedItems) {
        $("#selected_item").text("Number of species selected:"+allSelectedItems.length);
        //console.log(allSelectedItems.length);
    }
    */
    
    $('#re_enter').bind("cut copy paste", function(e) {
        e.preventDefault();
        alert("You cannot paste text into this textbox!");
        $('#re_enter').bind("contextmenu", function(e) {
            e.preventDefault();
        });
    });
    
    $("#demo").hide();
    $(".tree-multiselect").hide();
    $('#wait').hide();
    
    var csrftoken = getCookie('csrftoken');
    var upload_id = Sha256.hash(Math.random());
 	var uploadfileObj1 = $("#fileuploader_1").uploadFile({
        url:"/data_upload",
        multiple:true,
        dragDrop:false,
        maxFileCount:2,
        allowedTypes:"fastq,fq,gz",
        maxFileSize:21474836480,
        uploadStr:'<i class="glyphicon glyphicon-plus"></i>Add files...',
        uploadButtonClass:"btn btn-success fileinput-button",
        fileName:"myfile",
        autoSubmit:false,
        returnType:"json",
        sequential:true,
        sequentialCount:1,
        serialize:true,
        uploadQueueOrder:"bottom",
        showDelete:true,
        dynamicFormData: function() {
            var data = {'csrfmiddlewaretoken':csrftoken,
                        'upload_id':upload_id
                       };
            return data;
        },
        extraHTML:function() {
            var obj_rad_uploadfile = $(".rad_uploadfile_type");
            var htm_name = '';
            var htm_R1_checked = '';
            var htm_R2_checked = '';
            var htm_disabled = '';
            if(obj_rad_uploadfile.length > 0) {
                obj_rad_uploadfile.each(function(index) {
                    if($(this).is(':checked')) {
                        if($(this).val() == 'R1') htm_R2_checked = ' checked';
                        else if($(this).val() == 'R2') htm_R1_checked = ' checked';
                    }
                    if($(this).is(':disabled')) htm_disabled = ' disabled';
                });
                if(obj_rad_uploadfile.attr("name") == "uploadfile_type1") htm_name = 'uploadfile_type2';
                else htm_name = 'uploadfile_type1';
            }
            else {
                htm_name = 'uploadfile_type1';
                htm_R1_checked = ' checked';
            }
            
            return '<label class="radio-inline"> <input type="radio" class="rad_uploadfile_type" name="'+htm_name+'" id="'+htm_name+'_R1" value="R1"'+htm_R1_checked+htm_disabled+'>R1</input></label><label class="radio-inline"><input type="radio" class="rad_uploadfile_type" name="'+htm_name+'" id="'+htm_name+'_R2" value="R2"'+htm_R2_checked+htm_disabled+'>R2</input></label>';
        },
        onCancel: function(files,pd)
        {
            //console.log(JSON.stringify(files));
            //console.log(JSON.stringify(pd));
            $("#upload_button").hide();
        },
        onAbort: function(files,pd)
        {
            //console.log(JSON.stringify(files));
            //console.log(JSON.stringify(pd));
            $("#upload_button").hide();
        },
        onSuccess:function(files,data,xhr,pd){
            //console.log(JSON.stringify(files));
            //console.log(JSON.stringify(data));
            if(typeof(data['uploadfile_type1'])=='undefined')
            {
                upload_files_stat[data['uploadfile_type2']] = true;
            }
            else
            {
                upload_files_stat[data['uploadfile_type1']] = true;
            }
            //console.log(JSON.stringify(upload_files_stat));
            
            if(upload_files_stat['R1'] && upload_files_stat['R2'])
            {
                $("#upload_button").hide();
                $("#ref_upload").show();
                
                if(upload_files_stat['ref'])
                {
                    $("#upload_id").val(data['upload_id']);
                    $("#reads_url_upload").hide();
                    $("#reads_browser_upload").show();
                    $("#ref_url_upload").hide();
                    $("#ref_browser_upload").show();
                    $("input[id=from_browser]").prop("checked", true).attr("checked", true);
                    $("#fin_upload").show();
                    $("#upload_method").val($("input[name=rad_upload_method]:checked").val())
                    $("input[name=rad_upload_method]").attr("disabled", true);

                }
            }
        },
        deleteCallback: function (data, pd) {
            var post_data = {};
            Object.keys(data).forEach(function(key, index) {
                post_data[key] = this[key];
            }, data);
            $.post("/delete_upload", post_data,
            function (resp, textStatus, jqXHR) {
                //Show Message
                //console.log(JSON.stringify(resp));
            });
            
            $("#fin_upload").hide();
            $("#ref_upload").hide();
            $("#upload_button").hide();
            $("#upload_id").val('');
            $("#upload_method").val('')
            $("input[name=rad_upload_method]").attr("disabled", false);
            if(typeof(data['uploadfile_type1'])=='undefined')
            {
                upload_files_stat[data['uploadfile_type2']] = false;
            }
            else
            {
                upload_files_stat[data['uploadfile_type1']] = false;
            }
        }
	});
    
 	var uploadfileObj2 = $("#fileuploader_2").uploadFile({
        url:"/data_upload",
        multiple:false,
        dragDrop:false,
        maxFileCount:1,
        allowedTypes:"fasta,fa,fna,gz",
        maxFileSize:2147483648,
        uploadStr:'<i class="glyphicon glyphicon-plus"></i>Add a file...',
        uploadButtonClass:"btn btn-success fileinput-button",
        fileName:"myfile",
        autoSubmit:true,
        returnType:"json",
        sequential:true,
        sequentialCount:1,
        serialize:true,
        uploadQueueOrder:"bottom",
        showDelete:true,
        dynamicFormData: function() {
            var data = {'csrfmiddlewaretoken':csrftoken,
                        'upload_id':upload_id
                       };
            return data;
        },
        onSuccess:function(files,data,xhr,pd){
            //console.log(JSON.stringify(files));
            //console.log(JSON.stringify(data));
            upload_files_stat['ref'] = true;
            
            if(upload_files_stat['R1'] && upload_files_stat['R2'] && upload_files_stat['ref'])
            {
                $("#upload_id").val(data['upload_id']);
                $("#reads_url_upload").hide();
                $("#reads_browser_upload").show();
                $("#ref_url_upload").hide();
                $("#ref_browser_upload").show();
                $("input[id=from_browser]").prop("checked", true).attr("checked", true);
                $("#fin_upload").show();
                $("#upload_method").val($("input[name=rad_upload_method]:checked").val())
                $("input[name=rad_upload_method]").attr("disabled", true);
            }
        },
        deleteCallback: function (data, pd) {
            var post_data = {};
            Object.keys(data).forEach(function(key, index) {
                post_data[key] = this[key];
            }, data);
            $.post("/delete_upload", post_data,
            function (resp, textStatus, jqXHR) {
                //Show Message
                //console.log(JSON.stringify(resp));
            });
            
            $("#fin_upload").hide();
            $("#upload_id").val('');
            $("#upload_method").val('')
            $("input[name=rad_upload_method]").attr("disabled", false);
            upload_files_stat['ref'] = false;
        }
	});
    
    $("#upload_button").click(function()
    {
        $("input[name='uploadfile_type1']").attr("disabled", true);
        $("input[name='uploadfile_type2']").attr("disabled", true);
        uploadfileObj1.startUpload();
    });
    
    $("#reads_upload_area").change(function(){
        if(uploadfileObj1.getFileCount() == 2) {$("#upload_button").show();}
    });
    
    $("#reads_upload_area").on("click", ".rad_uploadfile_type", function(){
        var obj_rad_uploadfile = $(".rad_uploadfile_type");
        var current_inx = obj_rad_uploadfile.index(this);
        var corresponding_idx = (-1)*current_inx+3;
        obj_rad_uploadfile.removeAttr("checked");
        obj_rad_uploadfile.eq(current_inx).prop("checked", true).attr("checked", true);
        obj_rad_uploadfile.eq(corresponding_idx).prop("checked", true).attr("checked", true);
    });
    
    
    $("#reads_url_confirm_button").click(function(event){
        var str_url_R1 = $("#url_R1").val();
        var str_url_R2 = $("#url_R2").val();
        $("#url_R1_err").text("");
        $("#url_R2_err").text("");
        
        if(str_url_R1 == "" || str_url_R2 == "") {
            if(str_url_R1 == "") {$("#url_R1_err").text("*Required field.");}
            if(str_url_R2 == "") {$("#url_R2_err").text("*Required field.");}
        }
        else {
            $.ajax({
                type: "POST",
                dataType: "json",
                url: "/confirm_urls",
                data: {
                    'csrfmiddlewaretoken': csrftoken,
                    'url_R1': str_url_R1,
                    'url_R2': str_url_R2
                },
                error: function () {
                    // do nothing
                    alert('Failed to download from the URLs. Please contact the administrator.');
                },
                success: function (data) {
                    if(data['R1'] && data['R2']) { // both success
                        confirmed_urls_stat['reads'] = true;
                        $("#url_R1").attr("disabled", true);
                        $("#url_R2").attr("disabled", true);
                        $("#confirmed_url_R1").val(str_url_R1);
                        $("#confirmed_url_R2").val(str_url_R2);
                        $("#reads_url_confirm_button").hide();
                        $("#ref_upload").show();
                        
                        if(confirmed_urls_stat['ref']) {
                            $("#upload_id").val(upload_id);
                            $("#reads_browser_upload").hide();
                            $("#reads_url_upload").show();
                            $("#ref_browser_upload").hide();
                            $("#ref_url_upload").show();
                            $("input[id=from_url]").prop("checked", true).attr("checked", true);
                            $("#fin_upload").show();
                            $("#upload_method").val($("input[name=rad_upload_method]:checked").val())
                            $("input[name=rad_upload_method]").attr("disabled", true);
                        }
                    }
                    else { // R1 and/or R2 confirm error
                        confirmed_urls_stat['reads'] = false;
                        if(!data['R1']) {$("#url_R1_err").text("Error: "+data['R1_err']);}
                        if(!data['R2']) {$("#url_R2_err").text("Error: "+data['R2_err']);}
                    }                    
                }
            });
        }
    });
    
    $("#ref_url_confirm_button").click(function(event){
        var str_url_Rf = $("#url_Rf").val();
        $("#url_Rf_err").text("");
        
        if(str_url_Rf == "") {
            $("#url_Rf_err").text("*Required field.");
        }
        else {
            $.ajax({
                type: "POST",
                dataType: "json",
                url: "/confirm_urls",
                data: {
                    'csrfmiddlewaretoken': csrftoken,
                    'url_Rf': str_url_Rf
                },
                error: function () {
                    // do nothing
                    alert('Failed to download from the URLs. Please contact the administrator.');
                },
                success: function (data) {
                    if(data['Rf']) {
                        confirmed_urls_stat['ref'] = true;
                        $("#url_Rf").attr("disabled", true);
                        $("#confirmed_url_Rf").val(str_url_Rf);
                        $("#ref_url_confirm_button").hide();
                        
                        if(confirmed_urls_stat['reads']) {
                            $("#upload_id").val(upload_id);
                            $("#reads_browser_upload").hide();
                            $("#reads_url_upload").show();
                            $("#ref_browser_upload").hide();
                            $("#ref_url_upload").show();
                            $("input[id=from_url]").prop("checked", true).attr("checked", true);
                            $("#fin_upload").show();
                            $("#upload_method").val($("input[name=rad_upload_method]:checked").val())
                            $("input[name=rad_upload_method]").attr("disabled", true);
                        }
                    }
                    else {
                        confirmed_urls_stat['ref'] = false;
                        $("#url_Rf_err").text("Error: "+data['Rf_err']);
                    }                    
                }
            });
        }
    });
    
});

function treeOnChange(allSelectedItems, addedItems, removedItems) {
        $("#selected_item").text("Number of species selected:"+allSelectedItems.length);
        //console.log(allSelectedItems.length);
    }
$("input[name='tree']").change(function(){
        if($("#no_tree").is(':checked')){
            $("#selected_item").hide();
            $(".tree-multiselect").hide();
        }
        if($("#yes_tree").is(':checked')){
            
            if(ajaxcounter==0)
            { 
                
                $.ajax({
                    type: 'GET',
                    url: "./get_tree",
                    dataType: "json",
                    error: function () {
                        // do nothing
                        alert('loading failed!Please try again');
                    },
                    beforeSend: function() { $('#wait').show(); },
                    success: function (data) {
                        $("#demo").append(data['tree_content']);
                        
                        $("#demo").treeMultiselect({
                            startCollapsed: true,
                            searchable: true,
                            sortable: true,
                            onChange: treeOnChange,
                            maxSelections: 10
                            });
                        
                        $(".tree-multiselect").show();
                        $("#selected_item").show();
                        ajaxcounter=ajaxcounter+1;
                        //$("#message").text("success!!!!");
                    },
                    complete: function() { $('#wait').hide(); }
                })
                
            }
            else
            {
                //$("#message").text(ajaxcounter+" not reload again!!!!");
                $("#selected_item").show();
                $(".tree-multiselect").show();

            }
        }
        
});
$("input[name='denovo_setting']").change(function(){
        if($("#denovo_default").is(':checked')){
            $("table[name='denovo_table']").hide();
        }
        if($("#denovo_custom").is(':checked')){
            $("table[name='denovo_table']").show();
        }
        
});
$("input[name='ref_setting']").change(function(){
        if($("#ref_default").is(':checked')){
            $("table[name='ref_table']").hide();
        }
        if($("#ref_custom").is(':checked')){
            $("table[name='ref_table']").show();
        }
        
});
$("input[name='gene_pred']").change(function(){
        if($("#tool_Genemark").is(':checked')){
            $("#augustus").hide();
            $("table[name='pred_table']").hide();
        }
        if($("#tool_Augustus").is(':checked')){
            $("#augustus").show();
            if($("#aug_default").is(':checked')){
            $("table[name='pred_table']").hide();
            }
            if($("#aug_custom").is(':checked')){
                $("table[name='pred_table']").show();
            }
        }        
});
$("input[name='aug_setting']").change(function(){
        if($("#aug_default").is(':checked')){
            $("table[name='pred_table']").hide();
        }
        if($("#aug_custom").is(':checked')){
            $("table[name='pred_table']").show();
        }
        
});
$("input[name='pred_assm_setting']").change(function(){
        if($("#pred_assm_default").is(':checked')){
            $("table[name='pred_assm_table']").hide();
        }
        if($("#pred_assm_custom").is(':checked')){
            $("table[name='pred_assm_table']").show();
        }
        
});
$("input[name='go_setting']").change(function(){
        if($("#go_default").is(':checked')){
            $("table[name='go_table']").hide();
        }
        if($("#go_custom").is(':checked')){
            $("table[name='go_table']").show();
        }
        
});

$("input[name='rad_upload_method']").change(function(){
    if($("#from_browser").is(':checked')){
        $("#reads_url_upload").hide();
        $("#reads_browser_upload").show();
        $("#ref_url_upload").hide();
        $("#ref_browser_upload").show();
    }
    else if($("#from_url").is(':checked')){
        $("#reads_browser_upload").hide();
        $("#reads_url_upload").show();
        $("#ref_browser_upload").hide();
        $("#ref_url_upload").show();
    }
    
});

function validateEmail(email) {
  var re = /^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
  return re.test(email);
}

$("#submit").click(function() { 
    if(!validateEmail($("#email").val()))
    {
        alert("Email invalid!");
        return false;
    }        
    if($("#email").val() !=$("#re_enter").val())
    {
        alert("Email re-enter not matched!");
        return false;
    }   
    if($("#yes_tree").is(':checked'))
    {
        var tree_re=/^[A-Za-z0-9_]{1,10}$/;
        if(!tree_re.test($("#tree_sample_name").val()))
        {
            alert("Tree name invalid!");
            return false;
        }     

    }

});
