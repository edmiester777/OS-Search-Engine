<?php
require_once dirname(__FILE__).'/solr/Service.php';
define('SOLR_HOST', 'localhost');
define('SOLR_PORT', 8983);
define('SOLR_PATH', '/solr/search_engine/');
$is_query = isset($_GET['q']);
$solr = new Apache_Solr_Service(SOLR_HOST, SOLR_PORT, SOLR_PATH);
$q = "";
$results = array();
$count = 0;
$page = isset($_GET['page']) ? (int)$_GET['page'] : 1;
if($is_query){
	$q = strtolower($_GET['q']);
	$q = stripslashes($q);
	$terms = explode(" ", $q);
	if(!is_array($terms))
		$terms = array($q);
	$results = $solr->search($q, ($page - 1) * 20, 20, array(
		"fq"   => "title:['' TO *] AND content:['' TO *]",
		"qf"   => "url^15meta_keywords^10,title^5,meta_description^4,content^2",
		"fl"   => "*,score",
		"sort" => "score desc"
	), "POST");
	$count = $results->response->numFound;
	if($count > 0){
		$decoded = json_decode($results->getRawResponse(), true);
		$time_ms = (int)$decoded["responseHeader"]["QTime"];
		$exec_time = $time_ms / 1000;
		unset($decoded);
	}
}
?>
<html>
	<head>
		<title>Final Project</title>
		<link rel="stylesheet" href="http://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css">
		<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.12.4/jquery.min.js"></script>
		<script src="http://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js"></script>
		<script type="text/javascript">
			$(document).ready(function(){
				$('#search_query_form').submit(function(evt){
					evt.preventDefault();
					if($('#q').val().length == 0)
						return false;
					vals = $('#q').val().trim().split(/\s+/g);
					for(var i = 0; i < vals.length; ++i)
						vals[i] = encodeURIComponent(vals[i]);
					composed_query = vals.join('+');
					document.location = "index.php?q=" + composed_query;
					return false;
				});
				$("input").keypress(function(evt){
					if(evt.which == 13){
						evt.preventDefault();
						$('#search_query_form').submit();
					}
				});
			});
		</script>
	</head>
	<body>
		<div class="jumbotron text-center">
			<h1>Search Engine</h1>
			<p>
				<form id="search_query_form" method="GET" action="index.php">
					<input id="q" type="text" name="q" style="width:500px;" placeholder="Search" value="<?=$is_query ? $_GET['q'] : ""?>" />
				</form>
			</p>
		</div>
		<?php 
		if($is_query){
			?>
			<div class="container">
				<h5 class="text-center">
					Found <?=$count?> result<?=$count != 1 ? 's' : ''?> in <?=$exec_time?>s
				</h5>
				<?php
				if(count($results) == 0){
					?>
					<div class="row">
						<div class="col-lg-12">
							<h2>Sorry!</h2>
							<p>
								We couldn't find any results :(
							</p>
						</div>
					</div>
					<?php
				}
				else{
					foreach($results->response->docs as $doc){
						$is_https = $doc->getField('is_https')['value'];
						$url = "http".($is_https ? 's' : '').'://'.$doc->getField('url')['value'];
						$content = $doc->getField('meta_description')['value'];
						$min_content = $content;
						if(strlen($content) == 0){
							$content = $doc->getField('content')['value'];
							$min_content = (strlen($content) > 350 ? substr($content, 0, 350).'...' : $content);
						}
						$url_b = NULL;
						$title = $doc->getField('title')['value'];
						$url_b = bold_words_in_string($url, $terms);
						$title = bold_words_in_string($title, $terms);
						?>
						<div class="col-lg-12">
							<h3><a href="<?=$url?>"><?=$title?></a></h3>
							<p>
								<a href="<?=$url?>"><?=$url_b?></a><br />
								<?=ucfirst($min_content)?>
							</p>
						</div>
						<?php
					}
				}
				?>
				<div class="row">
					<div class="col-lg-12">
						<?php
						if($page > 1){
							output_page_link($page - 1, $q, 'Back');
						}
						if($page <= 5){
							for($i = 1; $i < $page; ++$i)
								output_page_link($i, $q);
						}
						else{
							output_page_link(1, $q);
							for($i = $page - 5; $i < $page; ++$i)
								output_page_link($i, $q);
						}
						output_page_link($page, $q, "<b>{$page}</b>");
						$max_pages = ceil($count / 20);
						$is_end_soon = ($max_pages - $page) < 5;
						$go_to =  $is_end_soon ? $max_pages : $page + 5;
						for($i = $page + 1; $i < $go_to; ++$i){
							output_page_link($i, $q);
						}
						if(!$is_end_soon)
							output_page_link($max_pages, $q);
						if($max_pages > $page){
							output_page_link($page + 1, $q, "Next");
						}
						?>
					</div>
				</div>
			</div>
			<?php
		}
		?>
	</body>
</html>

<?php
function bold_words_in_string($subject, $words){
	$words = array_unique($words);
	for($i = 0; $i < count($words); ++$i){
		$words[$i] = str_replace('/', '\\/', $words[$i]);
	}
	$regex = '/('.implode('|', $words).")/i";
	preg_match_all($regex, $subject, $matches);
	$all_matches = array();
	foreach($matches as $match_arr){
		foreach($match_arr as $word)
			$all_matches[]= $word;
	}
	$all_matches = array_unique($all_matches);
	foreach($all_matches as $word){
		$subject = str_replace($word, "<b>{$word}</b>", $subject);
	}
	return $subject;
}
function output_page_link($page_number, $query, $custom_text = NULL){
	?>
	<a href="http://localhost/?q=<?=str_replace(' ', '+', $query)?>&page=<?=$page_number?>"><?=$custom_text == NULL ? $page_number : $custom_text?></a>
	<?php
}
?>