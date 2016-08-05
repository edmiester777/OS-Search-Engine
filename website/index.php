<?php
require_once dirname(__FILE__).'/DatabaseConnector.class.php';
global $dbConn;
$is_query = isset($_GET['q']);
$q = "";
$results = array();
$count = 0;
if($is_query){
	$q = strtolower($_GET['q']);
	$terms = explode(" ", $q);
	$term_bind_queue = array();
	$term_binds = array();
	for($i = 0; $i < count($terms); ++$i){
		$term_bind_queue[]= ":term_{$i}";
		$term_binds[$term_bind_queue[$i]] = $terms[$i];
	}
	$query = implode(', ', $term_bind_queue);
	$results = $dbConn->executeQuery(
		"
		SELECT SQL_CALC_FOUND_ROWS
			DOMAINS.is_https,
		    DOMAINS.domain_name,
		    PATHS.path,
		    DETAILS.title,
		    DETAILS.description,
		    SUM(RANKING.rank) AS rank
		FROM paths AS PATHS
		LEFT JOIN keyword_ranking AS RANKING ON RANKING.path_id = PATHS.path_id
		LEFT JOIN keywords AS KW ON KW.keyword_id = RANKING.keyword_id
		LEFT JOIN page_details AS DETAILS ON DETAILS.path_id = PATHS.path_id
		LEFT JOIN domains AS DOMAINS ON DOMAINS.domain_id = PATHS.domain_id
		WHERE KW.keyword IN({$query}) AND rank > 0
		GROUP BY PATHS.path_id
		ORDER BY rank DESC
		LIMIT 0, 40
		",
		$term_binds
	);
	$count_query = $dbConn->executeQuery("SELECT FOUND_ROWS() AS count");
	$count = $count_query[0]["count"];
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
				<h2 class="text-center">
					Found <?=$count?> result<?=$count != 1 ? 's' : ''?>
				</h2>
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
					foreach($results as $result){
						$url = $result['is_https'] ? 'https://' : "http://";
						$url .= $result['domain_name'];
						$url .= $result['path'];
						?>
						<div class="row">
							<div class="col-lg-12">
								<h4>
									<a href="<?=$url?>"><?=$result['title']?></a>
								</h4>
								<p>
									<?=$result['description']?>
								</p>
							</div>
						</div>
						<?php
					}
				}
				?>
			</div>
			<?php
		}
		?>
	</body>
</html>