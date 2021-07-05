upload_files_stat={"R1":false, "R2":false, "long":false};
confirmed_urls_stat={"reads":false, "long":false};
var ajaxcounter=0;
$(document).ready(function () {
    $("table").hide(); 
    $("#augustus").hide();
    $("#upload_button").hide();
    $(".reads_url_upload").hide();
    $("#short_upload").hide();
    $("table[name='denovo_table_hybrid_only']").hide();
    $("#fin_upload").hide();
    $("#submission_panel").hide();
    // $("#ref_url_upload").hide();
    // $("#ref_upload").hide();
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
    // Short-Read Upload
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
                $("#use_hybrid").val($("input[name=rad_use_hybrid]:checked").val())
                $("input[name=rad_use_hybrid]").attr("disabled", true);
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
            
            $("#upload_button").hide();
            if(typeof(data['uploadfile_type1'])=='undefined')
            {
                upload_files_stat[data['uploadfile_type2']] = false;
            }
            else
            {
                upload_files_stat[data['uploadfile_type1']] = false;
            }
            $("#use_hybrid").val("0")
            $("input[name=rad_use_hybrid]").attr("disabled", false);
        }
    });
    // Long-Read Upload
     var uploadfileObj2 = $("#fileuploader_2").uploadFile({
        url:"/data_upload",
        multiple:false,
        dragDrop:false,
        maxFileCount:1,
        allowedTypes:"fastq,fq,gz",
        maxFileSize:21474836480,
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
                        'upload_id':upload_id,
                        'uploadfile_long': "long"
                       };
            return data;
        },
        onSuccess:function(files,data,xhr,pd){
            //console.log(JSON.stringify(files));
            //console.log(JSON.stringify(data));
            upload_files_stat['long'] = true;
            
            $("#upload_id").val(data['upload_id']);
            $(".reads_url_upload").hide();
            $(".reads_browser_upload").show();
            $("input[id=from_browser]").prop("checked", true).attr("checked", true);
            $("#fin_upload").show();
            $("#upload_method").val($("input[name=rad_upload_method]:checked").val())
            $("input[name=rad_upload_method]").attr("disabled", true);
            
            // Re-upload a long read file and short-read files have been uploaded
            if(upload_files_stat['R1'] && upload_files_stat['R2']) {
                $("#use_hybrid").val($("input[name=rad_use_hybrid]:checked").val())
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
            upload_files_stat['long'] = false;
            $("#use_hybrid").val("0")
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
    
    
    $("#short_url_confirm_button").click(function(event){
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
                        $("#short_url_confirm_button").hide();
                        $("#use_hybrid").val($("input[name=rad_use_hybrid]:checked").val())
                        $("input[name=rad_use_hybrid]").attr("disabled", true);
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
    
    $("#long_url_confirm_button").click(function(event){
        var str_url_long = $("#url_long").val();
        $("#url_long_err").text("");
        
        if(str_url_long == "") {
            $("#url_long_err").text("*Required field.");
        }
        else {
            $.ajax({
                type: "POST",
                dataType: "json",
                url: "/confirm_urls",
                data: {
                    'csrfmiddlewaretoken': csrftoken,
                    'url_Lr': str_url_long
                },
                error: function () {
                    // do nothing
                    alert('Failed to download from the URLs. Please contact the administrator.');
                },
                success: function (data) {
                    if(data['Lr']) {
                        confirmed_urls_stat['long'] = true;
                        $("#url_long").attr("disabled", true);
                        $("#confirmed_url_long").val(str_url_long);
                        $("#long_url_confirm_button").hide();
                        $("#upload_id").val(upload_id);
                        $(".reads_browser_upload").hide();
                        $(".reads_url_upload").show();
                        $("input[id=from_url]").prop("checked", true).attr("checked", true);
                        $("#fin_upload").show();
                        $("#upload_method").val($("input[name=rad_upload_method]:checked").val())
                        $("input[name=rad_upload_method]").attr("disabled", true);
                    }
                    else {
                        confirmed_urls_stat['long'] = false;
                        $("#url_long_err").text("Error: "+data['Lr_err']);
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
                    url: "/get_tree",
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
            $("table[name='denovo_table_hybrid_only']").hide();
        }
        if($("#denovo_custom").is(':checked')){
            $("table[name='denovo_table']").show();
            
            if($("#use_hybrid").val() == "1") {
                $("table[name='denovo_table_hybrid_only']").show();
            }
            else
            {
                $("table[name='denovo_table_hybrid_only']").hide();
            }
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
        $(".reads_url_upload").hide();
        $(".reads_browser_upload").show();
    }
    else if($("#from_url").is(':checked')){
        $(".reads_browser_upload").hide();
        $(".reads_url_upload").show();
    }
    
});

$("input[name='rad_use_hybrid']").change(function(){
    if($("#no_hybrid").is(':checked')){
        $("#short_upload").hide();
    }
    else if($("#yes_hybrid").is(':checked')){
        $("#short_upload").show();
    }
    
});

$("input[name='rad_long_read_platform']").change(function(){
    $("#long_read_platform").val($("input[name=rad_long_read_platform]:checked").val())
});

$("#accept_privacy_statement").change(function(){
    var check_val;
    check_val = $("#accept_privacy_statement:checked").val();
    if(check_val == "accept"){
        $("#submission_panel").show();
    }
    else {
        $("#submission_panel").hide();
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
    if(!$("input[name=rad_long_read_platform]").is(':checked'))
    {
        alert("Platform/Library for the uploaded reads not selected!");
        return false;
    }
    if($("#accept_privacy_statement:checked").val() != "accept")
    {
        alert("Must accept the Privacy Statement of MiDSystem!");
        return false;
    }
});
