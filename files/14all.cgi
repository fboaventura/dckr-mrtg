#!/usr/bin/perl -w
#
# 14all.cgi
#
# create html pages and graphics with rrdtool for mrtg + rrdtool
#
# (c) 1999-2002 bawidama@users.sourceforge.net
#
# use freely, but: NO WARRANTY - USE AT YOUR OWN RISK!
# license: GPL

# if MRTG_lib.pm (from mrtg) is not in the module search path (@INC)
# uncomment the following line and change the path appropriatly:
use lib qw(/usr/lib/mrtg2);

# if RRDs (rrdtool perl module) is not in the module search path (@INC)
# uncomment the following line and change the path appropriatly
# or use a LibAdd: setting in the config file
#use lib qw(/usr/local/rrdtool-1.0.38/lib/perl);

# RCS History - removed as it's available on the web

my $rcsid = '$Id: 14all.cgi,v 2.25 2003/01/05 18:39:51 bawidama Exp $';
my $subversion = (split(/ /,$rcsid))[2];
$subversion =~ m/^\d+\.(\d+)$/;
my $version = "14all.cgi 1.1p$1";

# my $DEBUG = 0; has gone - use config "14all*GraphErrorsToBrowser: 1"

use strict;
use CGI;
BEGIN { eval { require CGI::Carp; import CGI::Carp qw/fatalsToBrowser/ }
	if $^O !~ m/Win/i };
use MRTG_lib "2.090003";

sub main();
sub set_graph_params($$$$);
sub show_graph($$$);
sub show_log($$$);
sub show_dir($$$);

sub print_error($@);
sub intmax(@);
sub yesorno($);
sub get_graph_params($$$);
sub getdirwriteable($$);
sub getpngsize($);
sub errorpng();
sub gettextpic($);
sub log_rrdtool_call($$@);

# global, static vars
my ($cfgfile, $cfgfiledir);
my (@author, @style);

### where the mrtg.cfg file is
# anywhere in the filespace
#$cfgfile = '/home/mrtg/mrtg.cfg';
# relative to the script
#$cfgfile = 'mrtg.cfg';
# use this so 14all.cgi gets the cfgfile name from the script name
# (14all.cgi -> 14all.cfg)
$cfgfile = 'mrtg.cfg';

# if you want to store your config files in a different place than your cgis:
$cfgfiledir = '/etc/mrtg';

# $ENV{RRD_DEFAULT_FONT} = '/mrtg/fonts/opensans.ttf';

### customize the html pages
@author = ( -author => 'bawidama@users.sourceforge.net');
# one possibility to enable stylesheets (second is to use "AddHead[_]:..." in mrtg.cfg)
#@style = ( -style => { -src => 'general.css' });
###

# static data
my @headeropts = (@author, @style);

my %myrules = (
	'14all*errorpic' =>
		[sub{$_[0] && (-r $_[0] )}, sub{"14all*ErrorPic '$_[0]' not found/readable"}],
	'14all*grapherrorstobrowser' => [sub{1}, sub{"Internal Error"}],
	'14all*columns' =>
		[sub{int($_[0]) >= 1}, sub{"14all*Columns must be at least 1 (is '$_[0]')"}],
	'14all*rrdtoollog' =>
		[sub{$_[0] && (!-d $_[0] )}, sub{"14all*RRDToolLog must be a writable file"}],
	'14all*background' =>
		[sub{$_[0] =~ /^#[0-9a-f]{6}$/i}, sub{"14all*background colour not in form '#xxxxxx', x in [a-f0-9]"}],
	'14all*logarithmic[]' => [sub{1}, sub{"Internal Error"}],
	'14all*graphtotal[]' => [sub{1}, sub{"Internal Error"}],
	'14all*dontshowindexgraph[]' => [sub{1}, sub{"Internal Error"}],
	'14all*indexgraph[]' => [sub{1}, sub{"Internal Error"}],
	'14all*indexgraphsize[]' =>
		[sub{$_[0] =~ m/^\d+[,\s]+\d+$/o}, sub{"14all*indexgraphsize: need two numbers"}],
	'14all*maxrules[]' => [sub{1}, sub{"Internal Error"}],
	'14all*stackgraph[]' => [sub{1}, sub{"Internal Error"}],
);

my %graphparams = (
	'daily'   => ['-2000m', 'now',  300],
	'weekly'  => ['-12000m','now', 1800],
	'monthly' => ['-800h', 'now',  7200],
	'yearly'  => ['-400d', 'now', 86400],
	'daily.s' => ['-1250m', 'now',  300],
);

# the footer we print on every page
my $footer_template = <<"EOT";
<TABLE BORDER=0 CELLSPACING=0 CELLPADDING=0>
  <TR>
    <TD WIDTH=63><A ALT="MRTG"
    HREF="http://ee-staff.ethz.ch/~oetiker/webtools/mrtg/mrtg.html"><IMG
    BORDER=0 SRC="/mrtg-l.png"></A></TD>
    <TD WIDTH=25><A ALT=""
    HREF="http://ee-staff.ethz.ch/~oetiker/webtools/mrtg/mrtg.html"><IMG
    BORDER=0 SRC="/mrtg-m.png"></A></TD>
    <TD WIDTH=388><A ALT=""
    HREF="http://ee-staff.ethz.ch/~oetiker/webtools/mrtg/mrtg.html"><IMG
    BORDER=0 SRC="/mrtg-r.png"></A></TD>
  </TR>
</TABLE>
<TABLE BORDER=0 CELLSPACING=0 CELLPADDING=0>
  <TR VALIGN=top>
  <TD WIDTH=88 ALIGN=RIGHT><FONT FACE="Arial,Helvetica" SIZE=2>Version ${MRTG_lib::VERSION}</FONT></TD>
  <TD WIDTH=388 ALIGN=RIGHT><FONT FACE="Arial,Helvetica" SIZE=2>
  <A HREF="http://ee-staff.ethz.ch/~oetiker/">Tobias Oetiker</A>
  <A HREF="mailto:oetiker\@ee.ethz.ch">&lt;oetiker\@ee.ethz.ch&gt;</A> and
  <A HREF="http://www.bungi.com">Dave&nbsp;Rand</A>&nbsp;
  <A HREF="mailto:dlr\@bungi.com">&lt;dlr\@bungi.com&gt;</A>
  <TR VALIGN=top>
  <TD WIDTH=88 ALIGN=RIGHT><FONT FACE="Arial,Helvetica" SIZE=2><a
    href="http://my14all.sourceforge.net/">$version</a></FONT></TD>
  <TD WIDTH=388 ALIGN=RIGHT><FONT FACE="Arial,Helvetica" SIZE=2>
  Rainer&nbsp;Bawidamann&nbsp;
  <A HREF="mailto:bawidama\@users.sourceforge.net">&lt;bawidama\@users.sourceforge.net&gt;</A></FONT>
  </TD>
</TR>
</TABLE>
EOT

# global vars, persistent for speecyCGI/mod_perl
%my14all::config_cache = ();
$my14all::meurl = '';


# run main
main();
exit(0);
# end.

sub main() {
	if (!$cfgfile && $#ARGV == 0 && $ARGV[0] !~ m/=/ && !exists($ENV{QUERY_STRING})) {
		$cfgfile = shift @ARGV;
	}

	my %setup;
	# initialize CGI
	my $q = new CGI;
	$setup{q} = $q;

	# change for mrtg-2.9.*
	# look for the config file
	$my14all::meurl = $q->url(-relative => 1);
	ensureSL(\$cfgfiledir);
	my $l_cfgfile; # don't change what is set above in the CGI
	if (defined $q->param('cfg')) {
		$l_cfgfile = $q->param('cfg');
		# security fix: don't allow ./ in the config file name
		print_error($q, "Illegal characters in cfg param: ./")
			if $l_cfgfile =~ m'(^/)|(\./)';
		$l_cfgfile = $cfgfiledir.$l_cfgfile unless -r $l_cfgfile;
		print_error($q, "Cannot find the given config file: \<tt>$l_cfgfile\</tt>")
			unless -r $l_cfgfile;
	} elsif (!$cfgfile) {
		$l_cfgfile = $my14all::meurl;
		$l_cfgfile =~ s|.*\Q$MRTG_lib::SL\E||;
		$l_cfgfile =~ s/\.(cgi|pl|perl)$/.cfg/;
		#$my14all::meurl =~ m{\Q$MRTG_lib::SL\E([^\Q$MRTG_lib::SL\E]*)\.(cgi|pl)$};
		#$l_cfgfile = $1 . '.cfg';
		$l_cfgfile = $cfgfiledir.$l_cfgfile unless -r $l_cfgfile;
	} else {
		$l_cfgfile = $cfgfile;
	}

	# now we have the name of the config file.
	# we might already have it with speedyCGI or mod_perl
	my $read_file = 1;
	my @cfg_stat = stat($l_cfgfile);
	if (exists $my14all::config_cache{config}{$l_cfgfile}{mtime} &&
	    $cfg_stat[9] <= $my14all::config_cache{config}{$l_cfgfile}{mtime})
	{
		$read_file = 0;
	}

	# read the config file
	if ($read_file) {
		# wipe old config
		delete $my14all::config_cache{config}{$l_cfgfile}
			if exists $my14all::config_cache{config}{$l_cfgfile};
		my (@sorted, %config, %targets);
		readcfg($l_cfgfile, \@sorted, \%config, \%targets, "14all", \%myrules);
		my @processed_targets;
		cfgcheck(\@sorted, \%config, \%targets, \@processed_targets);
		# set default refresh
		if (exists $config{refresh} && yesorno($config{refresh})
				&& $config{refresh} !~ m/^\d*[1-9]\d*$/o) {
			$config{refresh} = $config{interval} * 60;
		}
		# store config in "cache"
		$my14all::config_cache{config}{$l_cfgfile}{sorted} = \@sorted;
		$my14all::config_cache{config}{$l_cfgfile}{config} = \%config;
		$my14all::config_cache{config}{$l_cfgfile}{targets} = \%targets;
		$my14all::config_cache{config}{$l_cfgfile}{processed_targets} = \@processed_targets;
		$my14all::config_cache{config}{$l_cfgfile}{mtime} = $cfg_stat[9];

		# add LibAdd from config for RRDs.pm
		if ($config{libadd}) {
			unshift @INC, $config{libadd};
		}
		# load the rrdtool perl extension
		eval "use RRDs 1.00038";
	}
	my $cfg = $my14all::config_cache{config}{$l_cfgfile};

	my $footer = $footer_template;
	# make sure icondir is set (should be done by mrtg)
	$cfg->{config}{icondir} ||= $cfg->{config}{workdir};
	# put icondir into footer
	$footer =~ s/##ICONDIR##/$cfg->{config}{icondir}/g;

	my $log = '_';
	if (defined $q->param('log')) {
		$log = $q->param('log');
	}
	# set timezone for rrdtool
	if ($cfg->{targets}{timezone}{$log}) {
		$ENV{"TZ"} = $cfg->{targets}{timezone}{$log};
	}

	### the main switch
	# the modes:
	# if parameter "dir" is given show a list of the targets in this "directory"
	# elsif parameter "png" is given show a graphic for the target given w/ parameter "log"
	# elsif parameter "log" is given show the page for this target
	# else show a list of directories and of targets w/o directory
	# parameter "cfg" can hold the name of the config file to use
	if (defined $q->param('dir')) {
		show_dir($cfg, $q, $q->param('dir'));
	} elsif (defined $q->param('png')) {
		show_graph($cfg, $q, $q->param('png'));
		exit(0); # don't show (html) footer
	} elsif (defined $q->param('log')) {
		show_log($cfg, $q, $q->param('log'));
	} else {
		show_dir($cfg, $q, '');
	}
	if (!$cfg->{targets}{options}{nobanner}{$log}) {
		print $footer;
	}
	print $q->end_html();
	exit(0);
}

sub set_graph_params($$$$) {
	# calculate graph params and store in config
	my ($cfg, $log, $png, $small) = @_;
	unless (exists $cfg->{targets}{target}{$log}) {
		return "target '$log' unknown";
	}
	my ($start, $end, $maxage);
	my $graphparams = $cfg->{targets}{"graph*$png"}{$log};
	if ($graphparams) {
		($start, $end, $maxage) = split(/[,\s]+/, $graphparams, 3);
	}
	unless ($start && $end && $maxage) {
		unless (exists $graphparams{$png}) {
			return "CGI call error: graph '$png' unknown";
		}
		($start, $end, $maxage) = @{$graphparams{$png}};
	}
	my ($xs, $ys);
	if ($small) {
		($xs, $ys) = (250, 100);
		($xs, $ys) = ($cfg->{targets}{'14all*indexgraphsize'}{$log} =~ m/(\d+)[,\s]+(\d+)/)
			if $cfg->{targets}{'14all*indexgraphsize'}{$log};
	} else {
		($xs, $ys) = ($cfg->{targets}{xsize}{$log} + 23, $cfg->{targets}{ysize}{$log});
	}
	unless ($xs && $ys) {
		return "cannot get image sizes for graph $png / target $log";
	}
	my $rrd = $cfg->{config}{logdir}.$cfg->{targets}{directory}{$log} . $log . '.rrd';
	# escape ':' and '\' with \ in $rrd
	# (rrdtool replaces '\:' by ':' and '\\' by '\')
	$rrd =~ s/([:\\])/\\$1/g;
	my $pngdir = getdirwriteable($cfg->{config}{imagedir}, $cfg->{targets}{directory}{$log});
	$png .= '-i' if $small;
	my $pngfile = "${pngdir}${log}-${png}.png";

	# build the rrd command line: set the starttime and the graphics format (PNG)
	my @args = ($pngfile, '-s', $start, '-e', $end, '-a', 'PNG');
	# if it's not a small picture set the legends
	my ($l1,$l2,$l3,$l4,$li,$lo) = ('','','','','','');
	my ($ri, $ro) = ('','');

	# set the size of the graph
	push @args, '-w', $xs, '-h', $ys;
	# set scale factor and legend defaults
	my $per_unit = 'Second';
	my $persec = 'Bytes';
	my $factor = 1; # should we scale the values?
	if ($cfg->{targets}{options}{perminute}{$log}) {
		$factor = 60; # perminute -> 60x
		$per_unit = 'Minute';
	} elsif ($cfg->{targets}{options}{perhour}{$log}) {
		$factor = 3600; # perhour -> 3600x
		$per_unit = 'Hour';
	}
	if ($cfg->{targets}{options}{bits}{$log}) {
		$factor *= 8; # bits instead of bytes -> 8x
		$persec = 'Bits';
	}
	# let the user give an arbitrary factor:
	if ($cfg->{targets}{factor}{$log} and
		$cfg->{targets}{factor}{$log} =~ m/^[-+]?\d+(.\d+)?([eE][+-]?\d+)?$/)
	{
		$factor *= 0+$cfg->{targets}{factor}{$log};
	}

	# check if only one value should be graphed (set vars for fast access)
	my $noi = $cfg->{targets}{options}{noi}{$log};
	my $noo = $cfg->{targets}{options}{noo}{$log};

	# prepare the legends
	if (!$small && !$cfg->{targets}{options}{nolegend}{$log}) {
		foreach (qw/legend1 legend2 legend3 legend4 legendi legendo legendy shortlegend/) {
			if ($cfg->{targets}{$_}{$log}) {
				$cfg->{targets}{$_}{$log} =~ s'&nbsp;' 'go; #'
				$cfg->{targets}{$_}{$log} =~ s/%/%%/go;
			}
		}
		if ($cfg->{targets}{ylegend}{$log}) {
			push @args, '-v', $cfg->{targets}{ylegend}{$log};
		} else {
			push @args, '-v', "$persec per $per_unit";
		}

		if ($cfg->{targets}{legend1}{$log}) {
			$l1 = ":".$cfg->{targets}{legend1}{$log}."\\l"; }
		else {
			$l1 = ":Incoming Traffic in $persec per $per_unit\\l"; }
		if ($cfg->{targets}{legend2}{$log}) {
			$l2 = ":".$cfg->{targets}{legend2}{$log}."\\l"; }
		else {
			$l2 = ":Outgoing Traffic in $persec per $per_unit\\l"; }
		if ($cfg->{targets}{legend3}{$log}) {
			$l3 = ":".$cfg->{targets}{legend3}{$log}."\\l"; }
		else {
			$l3 = ":Maximal 5 Minute Incoming Traffic\\l"; }
		if ($cfg->{targets}{legend4}{$log}) {
			$l4 = ":".$cfg->{targets}{legend4}{$log}."\\l"; }
		else {
			$l4 = ":Maximal 5 Minute Outgoing Traffic\\l"; }

		if (exists $cfg->{targets}{legendi}{$log}) {
			$li = $cfg->{targets}{legendi}{$log}; }
		else {	$li = "In: "; }
		$li =~ s':'\\:'; # ' quote :
		if (exists $cfg->{targets}{legendo}{$log}) {
			$lo = $cfg->{targets}{legendo}{$log}; }
		else {	$lo = "Out:"; }
		$lo =~ s':'\\:'; # ' quote :

		if ($cfg->{targets}{options}{integer}{$log}) {
			$li .= ' %9.0lf' if $li;
			$lo .= ' %9.0lf' if $lo;
			$ri = '%3.0lf%%';
			$ro = '%3.0lf%%';
		} else {
			$li .= ' %8.3lf' if $li;
			$lo .= ' %8.3lf' if $lo;
			$ri = '%6.2lf%%';
			$ro = '%6.2lf%%';
		}
		if (!exists($cfg->{targets}{kmg}{$log}) || $cfg->{targets}{kmg}{$log}) {
			$li .= ' %s' if $li;
			$lo .= ' %s' if $lo;
			if ($cfg->{targets}{kilo}{$log}) {
				push @args, '-b', $cfg->{targets}{kilo}{$log};
			}
			if ($cfg->{targets}{shortlegend}{$log}) {
				$li .= $cfg->{targets}{shortlegend}{$log} if $li;
				$lo .= $cfg->{targets}{shortlegend}{$log} if $lo;
			}
		}
	}
	my $pngchar = substr($png,0,1);
	if ($pngchar and $cfg->{targets}{unscaled}{$log} and
		   $cfg->{targets}{unscaled}{$log} =~ m/$pngchar/) {
		my $max = intmax($cfg->{targets}{maxbytes}{$log},
			$cfg->{targets}{maxbytes1}{$log},
			$cfg->{targets}{maxbytes2}{$log},
			$cfg->{targets}{absmax}{$log});
		$max *= $factor;
		push @args, '-l', 0, '-u', $max, '-r';
	} elsif (yesorno($cfg->{targets}{'14all*logarithmic'}{$log})) {
		push @args, '-o';
	}
	push @args,'--alt-y-mrtg','--lazy','-c','MGRID#ee0000','-c','GRID#000000';
	# contributed by Henry Chen: option to stack the two values
	# set the mode of the second line from config
	my $line2 = 'LINE1:';
	if (yesorno($cfg->{targets}{'14all*stackgraph'}{$log})) {
		$line2 = 'STACK:';
	}
	# now build the graph calculation commands
	# ds0/ds1 hold the normal data sources to graph/gprint
	my ($ds0, $ds1) = ('in', 'out');
	push @args, "DEF:$ds0=$rrd:ds0:AVERAGE", "DEF:$ds1=$rrd:ds1:AVERAGE";
	if (defined $cfg->{targets}{options}{unknaszero}{$log}) {
		push @args, "CDEF:uin=$ds0,UN,0,$ds0,IF",
			"CDEF:uout=$ds1,UN,0,$ds1,IF";
		($ds0, $ds1) = ('uin', 'uout');
	}
	if ($factor != 1) {
		# scale the values. we need a CDEF for this
		push @args, "CDEF:fin=$ds0,$factor,*","CDEF:fout=$ds1,$factor,*";
		($ds0, $ds1) = ('fin', 'fout');
	}
	my $maximum0 = $cfg->{targets}{maxbytes1}{$log} || $cfg->{targets}{maxbytes}{$log};
	my $maximum1 = $cfg->{targets}{maxbytes2}{$log} || $cfg->{targets}{maxbytes}{$log};
	$maximum0 = 1 unless $maximum0;
	$maximum1 = 1 unless $maximum1;
	# ps0/ps1 hold the percentage data source for gprint
	my ($ps0, $ps1) = ('pin', 'pout');
	push @args, "CDEF:pin=$ds0,$maximum0,/,100,*,$factor,/",
		"CDEF:pout=$ds1,$maximum1,/,100,*,$factor,/";

	if (yesorno($cfg->{targets}{'14all*graphtotal'}{$log})
			&& $small) {
		push @args, "CDEF:total=$ds0,$ds1,+", "LINE1:total#ffa050:Total AVG\\l";
	}
	# now for the peak graphs / maximum values
	# mx0/mx1 hold the maximum data source for graph/gprint
	my ($mx0, $mx1) = ($ds0, $ds1);
	# px0/px1 hold the maximum pecentage data source for gprint
	my ($px0, $px1) = ($ps0, $ps1);
	if (!$small) {
		# the defs for the maximum values: for the legend ('MAX') and probabely
		# for the 'withpeak' graphs
		push @args, "DEF:min=$rrd:ds0:MAX", "DEF:mout=$rrd:ds1:MAX";
		($mx0, $mx1) = ('min', 'mout');
		if (defined $cfg->{targets}{options}{unknaszero}{$log}) {
			push @args, "CDEF:umin=$mx0,UN,0,$mx0,IF",
				"CDEF:umout=$mx1,UN,0,$mx1,IF";
			($mx0, $mx1) = ('umin', 'umout');
		}
		if ($factor != 1) {
			# scale the values. we need a CDEF for this
			push @args, "CDEF:fmin=$mx0,$factor,*","CDEF:fmout=$mx1,$factor,*";
			($mx0, $mx1) = ('fmin', 'fmout');
		}
		# draw peak lines if configured
		if ($cfg->{targets}{withpeak}{$log} &&
				substr($png,0,1) =~ /[$cfg->{targets}{withpeak}{$log} ]/) {
			push @args, "AREA:".$mx0.$cfg->{targets}{rgb3}{$log}.$l3 unless $noi;
			push @args, $line2.$mx1.$cfg->{targets}{rgb4}{$log}.$l4 unless $noo;
			if (yesorno($cfg->{targets}{'14all*graphtotal'}{$log})) {
				push @args, "CDEF:mtotal=$mx0,$mx1,+", "LINE1:mtotal#ff5050:Total MAX\\l";
			}
		}
		push @args, "CDEF:pmin=$mx0,$maximum0,/,100,*,$factor,/",
			"CDEF:pmout=$mx1,$maximum1,/,100,*,$factor,/";
		($px0, $px1) = ('pmin', 'pmout');
	}
	# the commands to draw the values
	my (@hr1, @hr2);
	if (!$small && yesorno($cfg->{targets}{'14all*maxrules'}{$log})) {
		chop $l1; chop $l1; chop $l2; chop $l2;
		@hr1 = (sprintf("HRULE:%d#ff4400: MaxBytes1\\l",$maximum0*$factor));
		@hr2 = (sprintf("HRULE:%d#aa0000: MaxBytes2\\l",$maximum1*$factor));
	}
	push @args, "AREA:".$ds0.$cfg->{targets}{rgb1}{$log}.$l1, @hr1 unless $noi;
	push @args, $line2.$ds1.$cfg->{targets}{rgb2}{$log}.$l2, @hr2 unless $noo;
	if (!$small && !$cfg->{targets}{options}{nolegend}{$log}) {
		# print the legends
		# order matters so noi/noo makes this ugly
		if ($cfg->{targets}{options}{nopercent}{$log}) {
			push @args, "GPRINT:$mx0:MAX:Maximal $li" if $li && !$noi;
			push @args, "GPRINT:$mx1:MAX:Maximal $lo\\l" if $lo && !$noo;
			push @args, "GPRINT:$ds0:AVERAGE:Average $li" if $li && !$noi;
			push @args, "GPRINT:$ds1:AVERAGE:Average $lo\\l" if $lo && !$noo;
			push @args, "GPRINT:$ds0:LAST:Current $li" if $li && !$noi;
			push @args, "GPRINT:$ds1:LAST:Current $lo\\l" if $lo && !$noo;
		} else {
			push @args,
				"GPRINT:$mx0:MAX:Maximal $li",
				"GPRINT:$px0:MAX:($ri)" if $li && !$noi;
			push @args,
				"GPRINT:$mx1:MAX:Maximal $lo",
				"GPRINT:$px1:MAX:($ro)\\l" if $lo && !$noo;
			push @args,
				"GPRINT:$ds0:AVERAGE:Average $li",
				"GPRINT:$ps0:AVERAGE:($ri)" if $li && !$noi;
			push @args,
				"GPRINT:$ds1:AVERAGE:Average $lo",
				"GPRINT:$ps1:AVERAGE:($ro)\\l" if $lo && !$noo;
			push @args,
				"GPRINT:$ds0:LAST:Current $li",
				"GPRINT:$ps0:LAST:($ri)" if $li && !$noi;
			push @args,
				"GPRINT:$ds1:LAST:Current $lo",
				"GPRINT:$ps1:LAST:($ro)\\l" if $lo && !$noo;
		}
	}

	# store rrdtool arg list for speedCGI/mod_perl mode
	$cfg->{rrdargs}{$log}{$png}{args} = \@args;
	$cfg->{rrdargs}{$log}{$png}{pngdir} = $pngdir;
	$cfg->{rrdargs}{$log}{$png}{pngfile} = $pngfile;
	$cfg->{rrdargs}{$log}{$png}{maxage} = $maxage;
	return '';
}

sub show_graph($$$) {
	# send a graphic, create it if necessary
	my ($cfg, $q, $png) = @_;
	my $log = $q->param('log');
	my $small = $q->param('small') ? '-i' : '';

	my $errstr = '';

	if (!$log) {
		$errstr="CGI call error: missing param 'log'";
		goto ERROR;
	}
	unless (exists $cfg->{targets}{target}{$log}) {
		$errstr="target '$log' unknown";
		goto ERROR;
	}
	# fix a problem with indexmaker
	if ($small) {
		my %imaker = qw/day.s daily.s week.s weekly month.s monthly year.s yearly/;
		if (exists $imaker{$png}) {
			$png = $imaker{$png};
		}
	}
	my $argsref;
	if (!exists $cfg->{rrdargs}{$log}{"$png$small"}{args}) {
		$errstr = set_graph_params($cfg, $log, $png, $small);
		goto ERROR if $errstr;
	}
	$argsref = $cfg->{rrdargs}{$log}{"$png$small"}{args};

	# fire up rrdtool
	my ($a, $rrdx, $rrdy) = RRDs::graph(@$argsref);
	my $e = RRDs::error();
	log_rrdtool_call($cfg->{config}{'14all*rrdtoollog'},$e,'graph',$argsref);
	my $pngfile = $cfg->{rrdargs}{$log}{"$png$small"}{pngfile};
	if ($e) {
		my $pngdir = $cfg->{rrdargs}{$log}{"$png$small"}{pngdir};
		if (!-w $pngdir) {
			$errstr = "cannot write to graph dir $pngdir\nrrdtool error: $e";
		} elsif (-e $pngfile and !-w _) {
			$errstr = "cannot write $pngfile\nrrdtool error: $e";
		} elsif (-e $pngfile) {
			if (unlink($pngfile)) {
				# try rrdtool a second time
				($a, $rrdx, $rrdy) = RRDs::graph(@$argsref);
				$e = RRDs::error();
				log_rrdtool_call($cfg->{config}{'14all*rrdtoollog'},$e,'graph',$argsref);
				$errstr = $e ? $errstr."\nrrdtool error from 2. call: $e" : '';
			} else {
				$errstr = "cannot delete file $pngfile: $!";
			}
		} else {
			$errstr = "cannot create graph\nrrdtool error: $e";
		}
	}
	unless ($errstr) {
		if (open(PNG, "<$pngfile")) {
			my $maxage = $cfg->{rrdargs}{$log}{"$png$small"}{maxage};
			print $q->header(-type => "image/png", -expires => "+${maxage}s");
			binmode(PNG); binmode(STDOUT);
			while(read PNG, my $buf, 16384) { print STDOUT $buf; }
			close PNG;
			return;
		}
		$errstr = "cannot read graph file: $!";
	}
	ERROR:
	if (yesorno($cfg->{config}{'14all*grapherrorstobrowser'})) {
		my ($errpic, $format) = gettextpic($errstr);
		print $q->header(-type => $format, -expires => 'now');
		binmode(STDOUT);
		print $errpic;
		return;
	}
	$log ||= '_';
	if (defined $cfg->{targets}{options}{'14all*errorpic'}{$log} &&
			open(PNG, $cfg->{targets}{options}{'14all*errorpic'}{$log})) {
		print $q->header(-type => "image/png", -expires => 'now');
		binmode(PNG); binmode(STDOUT);
		while(read PNG, my $buf,16384) { print STDOUT $buf; }
		close PNG;
		return;
	}
	print $q->header(-type => "image/png", -expires => 'now');
	binmode(STDOUT);
	print pack("C*", errorpng());
}

sub show_log($$$) {
	# show the graphics for one target
	my ($cfg, $q, $log) = @_;
	print_error($q,"Target '$log' unknown") if (!exists $cfg->{targets}{target}{$log});
	my $title;
	# user defined title?
	if ($cfg->{targets}{title}{$log}) {
		$title = $cfg->{targets}{title}{$log};
	} else {
		$title = "MRTG/RRD - Target $log";
	}
	my @httphead;
	push @httphead, (-expires => '+' . int($cfg->{config}{interval}) . 'm');
	if (yesorno($cfg->{config}{refresh})) {
		push @httphead, (-refresh => $cfg->{config}{refresh});
	}
	my @htmlhead = (-title => $title, @headeropts,
		-bgcolor => $cfg->{targets}{background}{$log});
	if ($cfg->{targets}{addhead}{$log}) {
		push @htmlhead, (-head => $cfg->{targets}{addhead}{$log});
	}
	print $q->header(@httphead), $q->start_html(@htmlhead);
	# user defined header line? (should exist as mrtg requires it)
	print $cfg->{targets}{pagetop}{$log},"\n";
	my $rrd = $cfg->{config}{logdir}.$cfg->{targets}{directory}{$log} . $log . '.rrd';
	my $lasttime = RRDs::last($rrd);
	log_rrdtool_call($cfg->{config}{'14all*rrdtoollog'},'','last',$rrd);
	print $q->hr,
		"The statistics were last updated: ",$q->b(scalar(localtime($lasttime))),
		$q->hr if $lasttime;
	my $sup = $cfg->{targets}{suppress}{$log} || '';
	my $url = "$my14all::meurl?log=$log";
	my $tmpcfg = $q->param('cfg');
	$url .= "&cfg=$tmpcfg" if defined $tmpcfg;
	$url .= "&png";
	# the header lines and tags for the graphics
	my $pngdir = getdirwriteable($cfg->{config}{imagedir}, $cfg->{targets}{directory}{$log});
	if ($sup !~ /d/) {
		print $q->h2("'Daily' graph (5 Minute Average)"),"\n",
			$q->img({src => "$url=daily", alt => "daily-graph",
				getpngsize("$pngdir$log-daily.png")}
			), "\n";
	}
	if ($sup !~ /w/) {
		print $q->h2("'Weekly' graph (30 Minute Average)"),"\n",
			$q->img({src => "$url=weekly", alt => "weekly-graph",
				getpngsize("$pngdir$log-weekly.png")}
			), "\n";
	}
	if ($sup !~ /m/) {
		print $q->h2("'Monthly' graph (2 Hour Average)"),"\n",
			$q->img({src => "$url=monthly", alt => "monthly-graph",
				getpngsize("$pngdir$log-monthly.png")}
			), "\n";
	}
	if ($sup !~ /y/) {
		print $q->h2("'Yearly' graph (1 Day Average)"),"\n",
			$q->img({src => "$url=yearly", alt => "yearly-graph",
				getpngsize("$pngdir$log-yearly.png")}
			), "\n";
	}
	if ($cfg->{targets}{pagefoot}{$log}) {
		print $cfg->{targets}{pagefoot}{$log};
	}
}

sub show_dir($$$) {
	# if no parameter - show a list of directories and targets
	#    without "Directory[...]" (aka root-targets)
	# else show a list of targets in the given directory
	my ($cfg, $q, $dir) = @_;
	my @httphead;
	push @httphead, (-expires =>
		($dir ? '+' . int($cfg->{config}{interval}) . 'm' : '+1d') );
	if (yesorno($cfg->{config}{refresh})) {
		push @httphead, (-refresh => $cfg->{config}{refresh});
	}
	push @headeropts, (-bgcolor => ($cfg->{config}{'14all*background'} || '#ffffff'));
	my @htmlhead = (-title =>
		($dir ? "MRTG/14all - Group $dir" : "MRTG/14all $version"),
		@headeropts);
	print $q->header(@httphead), $q->start_html(@htmlhead);
	my (@dirs, %dirs, @logs);
	# get the list of directories and "root"-targets
	# or get list of targets from given directory
	foreach my $tar (@{$cfg->{sorted}}) {
		next if $tar =~ m/^[_\$\^]$/; # pseudo targets
		if ($cfg->{targets}{directory}{$tar}) {
			if ($dir) {
				# show a specified dir. check this targets dir against specified
				if ($dir eq $cfg->{targets}{directory}{$tar}) {
					# target is from specified dir
					push @logs, $tar;
				}
				next;
			}
			next if exists $dirs{$cfg->{targets}{directory}{$tar}};
			$dirs{$cfg->{targets}{directory}{$tar}} = $tar;
			push @dirs, $cfg->{targets}{directory}{$tar};
		} elsif (!$dir) {
			# showing 'homepage', add this target
			push @logs, $tar;
		}
	}
	my $cfgstr = (defined $q->param('cfg') ? "&cfg=".$q->param('cfg') : '');
	print $q->h1("Available Targets"),"\n";
	my $confcolumns = $cfg->{config}{'14all*columns'} || 2;
	if ($#dirs > -1) {
		print $q->h2("Directories"),"\n\<table width=100\%>\n";
		my $column = 0;
		foreach my $tar (@dirs) {
			print '<tr>' if $column == 0;
			(my $link = $tar) =~ s/ /\+/g;
			chop $tar; # remove / for display (from ensureSL)
			print $q->td($q->a({href => "$my14all::meurl?dir=$link$cfgstr"},
				$tar)),"\n";
			$column++;
			if ($column >= $confcolumns) {
				$column = 0;
				print '</tr>';
			}
		}
		if ($column != 0 and $column < $confcolumns) {
			print '<td>&nbsp;</td>' x ($confcolumns - $column),"\</tr>\n";
		}
		print '</table><hr>';
	}
	my $pngdir = getdirwriteable($cfg->{config}{imagedir},$dir);
	if ($#logs > -1) {
		print $q->h2("Targets"),"\n\<table width=100\%>\n";
		my $column = 0;
		foreach my $tar (@logs) {
			my $small = 0;
			unless (yesorno($cfg->{targets}{'14all*dontshowindexgraph'}{$tar})) {
				$small = $cfg->{targets}{'14all*indexgraph'}{$tar};
				$small = 'daily.s' unless $small;
			}
			next if $tar =~ m/^[\$\^_]$/; # _ is not a real target
			print '<tr>' if $column == 0;
			print '<td>',
				$q->p($q->a({href => "$my14all::meurl?log=$tar$cfgstr"}, $cfg->{targets}{title}{$tar}));
			print $q->a({href => "$my14all::meurl?log=$tar$cfgstr"},
				$q->img({src => "$my14all::meurl?log=$tar&png=$small&small=1$cfgstr",
					alt => "index-graph",
					getpngsize("$pngdir$tar-$small-i.png")}))
				if $small;
			print "\</td>\n";
			$column++;
			if ($column >= $confcolumns) {
				$column = 0;
				print '</tr>';
			}
		}
		if ($column != 0 and $column < $confcolumns) {
			print '<td>&nbsp;</td>' x ($confcolumns - $column),"\</tr>\n";
		}
		print '</table>';
	}
}

sub print_error($@)
{
	my $q = shift;
	print $q->header(),
		$q->start_html(
			-title => 'MRTG/RRD index.cgi - Script error',
			-bgcolor => '#ffffff'
		),
		$q->h1('Script Error'),
		@_, $q->end_html();
	exit 0;
}

sub intmax(@)
{
	my (@p) = @_;
	my $max = 0;
	foreach my $n (@p) {
		$max = int($n) if defined $n and int($n) > $max;
	}
	return $max;
}

sub yesorno($)
{
	my $opt = shift;
	return 0 unless defined $opt;
	return 0 if $opt =~ /^((no?)|(false)|0)$/i;
	return 1;
}

sub getdirwriteable($$)
{
	my ($base, $sub) = @_;
	$base .= $MRTG_lib::SL . $sub if $sub;
	ensureSL(\$base);
	if (!-w $base) {
		if ($^O =~ m/Win/i) {
			$base = $ENV{'TEMP'};
			$base = $ENV{'TMP'} unless $base;
			$base = $MRTG_lib::SL unless $base;
			ensureSL(\$base);
		} else {
			$base = '/tmp/';
		}
	}
	return $base;
}

use IO::File;

sub pngstring() { return chr(137)."PNG".chr(13).chr(10).chr(26).chr(10); };

sub getpngsize($)
{
	my ($file) = @_;
	my $fh = new IO::File $file;
	return () unless defined $fh;
	my $line;
	if (sysread($fh, $line, 8) != 8 or $line ne pngstring()) {
		$fh->close;
		return ();
	}
	CHUNKS: while(1) {
		last CHUNKS if (sysread($fh, $line, 8) != 8);
		my ($chunksize, $type) = unpack "Na4", $line;
		if ($type ne "IHDR") {
			last CHUNKS if (sysread($fh, $line, $chunksize + 4) != $chunksize + 4);
			next CHUNKS;
		}
		last CHUNKS if (sysread($fh, $line, 8) != 8);
		$fh->close;
		my ($x, $y) = unpack("NN", $line);
		return ('-width' => "$x", '-height' => "$y");
	}
	$fh->close;
	return ();
}

# this data contains a small png with the text:
# "error: cannot create graph"

sub errorpng()
{
	return (
		137,80,78,71,13,10,26,10,0,0,0,13,73,72,68,82,0,0,0,187,0,0,0,29,4,3,0,
		0,0,0,251,0,170,0,0,0,4,103,65,77,65,0,0,177,143,11,252,97,5,0,0,0,30,80,
		76,84,69,255,0,0,255,93,93,255,128,128,255,155,155,255,176,176,255,195,
		195,255,212,212,255,227,227,255,241,241,255,255,255,17,191,146,253,0,0,
		0,56,116,69,88,116,83,111,102,116,119,97,114,101,0,88,86,32,86,101,114,
		115,105,111,110,32,51,46,49,48,97,32,32,82,101,118,58,32,49,50,47,50,57,
		47,57,52,32,40,80,78,71,32,112,97,116,99,104,32,49,46,50,41,221,21,46,73,
		0,0,2,40,73,68,65,84,120,218,237,147,177,107,219,64,20,198,159,34,233,92,
		109,130,180,132,108,55,180,78,189,169,113,8,220,166,80,106,208,230,102,
		48,237,118,56,246,153,219,28,7,2,183,165,77,23,109,142,101,157,244,254,
		219,62,73,198,113,106,211,150,144,108,254,166,143,167,79,63,221,125,167,
		3,216,107,175,189,94,65,136,56,223,26,58,166,224,207,71,6,114,3,175,148,
		220,10,136,66,47,183,134,44,254,115,114,48,252,55,126,87,192,92,248,24,
		254,237,173,70,110,246,95,120,182,184,17,231,242,4,103,160,79,34,213,12,
		117,148,224,204,205,211,159,96,205,18,24,254,162,26,105,189,198,66,29,149,
		96,80,10,172,29,64,154,91,55,83,30,22,92,124,43,33,152,60,86,75,229,196,
		172,204,68,42,83,85,114,157,70,4,97,182,218,121,121,150,187,56,41,0,111,
		75,254,253,54,141,197,13,64,203,154,184,138,78,114,223,158,47,222,229,156,
		28,128,95,104,235,150,182,115,159,244,133,53,211,160,208,215,27,71,43,153,
		253,36,238,223,23,96,250,250,42,84,43,188,55,58,180,174,117,16,202,208,
		156,166,97,114,87,237,185,211,239,72,138,230,78,217,30,126,200,220,204,
		35,199,225,227,67,139,240,167,189,11,33,197,244,120,17,60,180,178,39,229,
		60,128,136,217,156,74,211,117,227,53,30,18,164,29,211,115,11,186,155,1,
		155,87,120,93,157,123,204,104,77,145,65,194,215,14,68,228,90,119,9,30,173,
		148,108,22,72,246,20,63,167,4,91,64,71,234,213,48,116,204,89,193,31,241,
		57,28,173,240,46,167,104,214,237,30,229,135,21,158,92,8,162,239,85,209,
		100,22,72,17,251,187,241,94,93,14,64,151,6,250,171,143,108,225,173,241,
		235,114,146,233,177,172,162,142,13,174,91,85,57,228,160,41,39,3,205,147,
		166,156,77,60,98,86,227,65,163,13,117,243,189,35,196,31,30,150,107,124,
		36,176,228,111,170,67,71,12,235,232,172,133,101,118,128,146,28,253,160,
		77,52,193,84,138,20,227,77,188,82,106,232,73,104,115,120,171,46,160,71,
		3,26,58,131,49,135,193,229,136,238,141,130,17,244,184,171,46,193,165,39,
		78,239,170,142,142,67,71,125,30,194,32,38,71,249,193,200,82,212,31,183,
		99,241,101,76,247,207,219,125,223,158,41,49,111,126,134,202,70,47,9,110,
		228,151,230,238,21,241,123,237,245,162,250,13,181,158,203,16,233,3,210,
		153,0,0,0,7,116,73,77,69,7,208,1,19,13,28,15,223,54,180,209,0,0,0,0,73,
		69,78,68,174,66,96,130
	);
}

sub gettextpic($) {
	my ($text) = @_;
	my @textsplit = split(/\n/, $text);
	my $len = 0;
	my $max = sub { $_[0] > $_[1] ? $_[0] : $_[1] };
	my @rrdargs;
	foreach (@textsplit) {
		$len = &$max($len, length($_));
		push @rrdargs, "COMMENT:$_\\l";
	}
	eval { require GD; 1; };
	unless ($@) {
		my $ys = @textsplit * (GD::gdMediumBoldFont()->height + 5);
		my $xs = $len * GD::gdMediumBoldFont()->width();
		my $im = new GD::Image($xs + 30, $ys + 20);
		my $back = $im->colorAllocate(255,255,255);
		$im->transparent($back);
		my $red = $im->colorAllocate(255,0,0);
		$im->filledRectangle(0,0,$xs-1,$ys-1,$back);
		my $starty = 10;
		foreach $text (@textsplit) {
			$im->string(GD::gdMediumBoldFont(), 10, $starty, $text, $red);
			$starty += 5 + GD::gdMediumBoldFont()->height;
		}
		binmode(STDOUT);
		if ($GD::VERSION lt '1.20') {
			#eval 'print $im->gif';
			return ($im->gif(), 'image/gif');
		} elsif ($GD::VERSION ge '1.20') {
			return ($im->png(), 'image/png');
		}
	}
	if ($ENV{MOD_PERL}) {
		# forking a RRDs child doesn't work with mod_perl
		return (pack("C*", errorpng()), 'image/png');
	}
	# create a graphic with rrdtool
	$len = &$max($len*6-60,50);
	unshift @rrdargs, ('-', '-w', $len, '-h', 10, '-c', 'FONT#ff0000');
	my $pid = open(P, "-|");
	unless (defined $pid) {
		return (pack("C*", errorpng()), 'image/png');
	}
	unless ($pid) {
		RRDs::graph(@rrdargs);
		exit 0;
	}
	local $/ = undef;
	my $png = <P>;
	close P;
	unless (defined $png) {
		return (pack("C*", errorpng()), 'image/png');
	}
	return ($png, 'image/png');
}

sub log_rrdtool_call($$@) {
    my ($logfile, $error, @args) = @_;
	return unless yesorno($logfile);
	unless (open(LOG, '>>'.$logfile)) {
		print STDERR "cannot log rrdtool call: $!\n";
		return;
	}
	print LOG "\n# call to rrdtool:\nrrdtool ";
    foreach my $arg (@args) {
        if (ref($arg) eq 'ARRAY') {
            print LOG join(' ',@$arg),' ';
        } else {
            print LOG $arg," ";
        }
    }
    print LOG "\n";
	if ($error) {
		print LOG "# gave ERROR: $error\n";
	} else {
		print LOG "# completed without error\n";
	}
	close LOG;
}
