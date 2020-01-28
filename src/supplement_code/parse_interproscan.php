<?php
$arr_pathway_db = array('GO', 'KEGG', 'REACTOME', 'METACYC');

$stderr_fp = fopen('php://stderr', 'a');
if($argc == 1 || $argc > 3)
{
	show_stderr("Usage: php parse_interproscan.php <tabular file> [GO (Default)|KEGG|Reactome|MetaCyc]\n");
	exit;
}
if(!isset($argv[2])) {$argv[2] = 'GO';}

// Check input error, or run
if(!file_exists($argv[1]))
{
	show_stderr('Error: cannot load `' . $argv[1] . "': No such file or directory\n");
	die;
}
elseif(!in_array(strtoupper($argv[2]), $arr_pathway_db))
{
	show_stderr('Error: type not found `' . $argv[2] . "': Supporting types for GO, KEGG, Reactome, MetaCyc\n");
	die;
}
else
{
	$fp = fopen($argv[1], 'r');
	$arr_lines = array();
	while(!feof($fp))
	{
		$line = trim(fgets($fp));
		if($line == '') {continue;}

		$arr_contents = explode("\t", $line);

		// Header definition from: https://github.com/ebi-pf-team/interproscan/wiki/OutputFormats
		$str_Protein_Accession = $arr_contents[0];
		$str_Sequence_MD5 = $arr_contents[1];
		$int_Sequence_Length = $arr_contents[2];
		$str_Analysis = $arr_contents[3];
		$str_Signature_Accession = $arr_contents[4];
		$str_Signature_Description = $arr_contents[5];
		$int_Start_location = $arr_contents[6];
		$int_Stop_location = $arr_contents[7];
		$flt_Score = $arr_contents[8];
		$str_Status = $arr_contents[9];
		$str_Date = $arr_contents[10];
		$str_InterPro_Accession = isset($arr_contents[11]) ? $arr_contents[11]:'';
		$str_InterPro_Description = isset($arr_contents[12]) ? $arr_contents[12]:'';
		$str_GO_Accession = isset($arr_contents[13]) ? $arr_contents[13]:'';
		$str_Pathway_Accession = isset($arr_contents[14]) ? $arr_contents[14]:'';
		
		switch(strtoupper($argv[2]))
		{
			case 'GO':
				foreach(explode('|', $str_GO_Accession) as $str_go_acc)
				{
					if($str_go_acc == '') {continue;}
					$arr_lines[] = "$str_Protein_Accession\t$str_go_acc";
				}
				break;
				
			case 'KEGG':
				foreach(explode('|', $str_Pathway_Accession) as $str_pathway_acc)
				{
					if($str_pathway_acc == '') {continue;}
					if(substr($str_pathway_acc, 0, 6) == 'KEGG: ')
					{
						$tmp_id = 'map';
						for($i=6; $i<strlen($str_pathway_acc); $i++)
						{
							if($str_pathway_acc[$i] != '+') {$tmp_id .= $str_pathway_acc[$i];}
							else {break;}
						}
						$arr_lines[] = "$str_Protein_Accession\t$tmp_id";
					}
				}
				break;
				
			case 'REACTOME':
			
			case 'METACYC':
			
			default:
				show_stderr($argv[2] . " has not been supported\n");
				exit;
		}
	}
	fclose($fp);
	
	//Output parsed results here!
	//var_dump(get_GO_annotation(array_unique($arr_lines)));
	switch(strtoupper($argv[2]))
	{
		case 'GO':
			array_output(get_GO_annotation(array_unique($arr_lines)));
			break;
		
		case 'KEGG':
			array_output(get_KEGG_annotation(array_unique($arr_lines)));
			break;
	}
	
}

function get_KEGG_annotation($arr_input) // returen an array
{
	$arr_return = array();
	$arr_uniq_kegg = array();
	@$fp = fopen(pathinfo($_SERVER['PHP_SELF'], PATHINFO_DIRNAME).'/KEGG_list.txt', 'r');
	if($fp === false)
	{
		show_stderr("Warning: KEGG_list.txt cannot found. Try to get a list from KEGG's website ... ");
		
		// Getting from KEGG API
		$url = 'http://rest.kegg.jp/list/pathway';
		$handle = fopen($url, 'r');
		if (false === $handle) {
			show_stderr("Failed.\nError: failed to open URL: $url\n");
			die;
		}
		$arr_lines = explode("\n", stream_get_contents($handle));
		fclose($handle);
		$fp_list = fopen(pathinfo($_SERVER['PHP_SELF'], PATHINFO_DIRNAME).'/KEGG_list.txt', 'w'); // Making a list automatically
		foreach($arr_lines as $line)
		{
			$line = trim($line);
			if($line == '') {continue;}
			$arr_contents = explode("\t", $line);
			$arr_contents[0] = substr($arr_contents[0], 5); //Removing the prefix "path:"
			if(!isset($arr_contents[1])) {$arr_contents[1] = '';}
			$arr_uniq_kegg[$arr_contents[0]] = $arr_contents[1];
			fwrite($fp_list, $arr_contents[0]."\t".$arr_contents[1]."\n");
		}
		fclose($fp_list);
		show_stderr("OK.\n");
	}
	else
	{
		$arr_lines = array();
		while(!feof($fp))
		{
			$line = trim(fgets($fp));
			if($line == '') {continue;}

			$arr_contents = explode("\t", $line);
			$arr_uniq_kegg[$arr_contents[0]] = $arr_contents[1];
		}
		fclose($fp);
	}
	
	foreach($arr_input as $str_input_contents)
	{
		$arr_input_contents = explode("\t", $str_input_contents);
		
		if(!isset($arr_uniq_kegg[$arr_input_contents[1]]))
		{
			$annotate = function($kegg_id) {
			$url = 'http://rest.kegg.jp/list/'.$kegg_id;
			$handle = fopen($url, 'r');
			if (false === $handle) {
				show_stderr("Warning: failed to open URL: $url\n");
				return '';
			}
			$contents = trim(stream_get_contents($handle));
			fclose($handle);
			if($contents == '') {return '';}
			else {return array_pop(explode("\t", $contents));}
			};
			
			$arr_uniq_kegg[$arr_input_contents[1]] = $annotate($arr_input_contents[1]);
		}
		
		array_push($arr_input_contents, $arr_uniq_kegg[$arr_input_contents[1]]);
		$arr_return[] = $arr_input_contents;
	}
	
	return $arr_return;
}

function get_GO_annotation($arr_input) // returen an array
{
	$arr_return = array();
	$arr_uniq_go = array();
	@$fp = fopen(pathinfo($_SERVER['PHP_SELF'], PATHINFO_DIRNAME).'/GOterm_list.txt', 'r');
	if($fp === false)
	{
		show_stderr("Warning: GOterm_list.txt cannot found. Try to get annotation from online. It may cause the processing slowly.\n");
	}
	else
	{
		$arr_lines = array();
		while(!feof($fp))
		{
			$line = trim(fgets($fp));
			if($line == '') {continue;}

			$arr_contents = explode("\t", $line);
			$arr_uniq_go[$arr_contents[0]] = array($arr_contents[1], $arr_contents[2]);
		}
		fclose($fp);
	}
	
	foreach($arr_input as $str_input_contents)
	{
		$arr_input_contents = explode("\t", $str_input_contents);
		
		if(!isset($arr_uniq_go[$arr_input_contents[1]]))
		{
			//show_stderr("Search ".$arr_input_contents[1]." online\n");
			$annotate = function($go_id) {
			$url = 'https://rest.ensembl.org/ontology/id/'.$go_id.'?content-type=application/json';
			$handle = fopen($url, 'r');
			if (false === $handle) {
				show_stderr("Error: failed to open URL: $url\n");
				die;
			}
			$contents = stream_get_contents($handle);
			$obj_contents = json_decode($contents);
			fclose($handle);
			
			return array($obj_contents->name, $obj_contents->namespace);
			};
			
			$arr_uniq_go[$arr_input_contents[1]] = $annotate($arr_input_contents[1]);
		}
		
		$arr_return[] = array_merge($arr_input_contents, $arr_uniq_go[$arr_input_contents[1]]);
	}
	
	return $arr_return;
}

function show_stderr($e)
{
	$stderr_fp = fopen('php://stderr', 'a');
	fwrite($stderr_fp, $e);
	fclose($stderr_fp);
}

function array_output($in_array)
{
	foreach($in_array as $arr_anno_lines)
	{
		echo implode("\t", $arr_anno_lines)."\n";
	}
}
?>