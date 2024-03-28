#!/usr/bin/perl -w
#
# 14all.cgi
#
# create html pages and graphics with rrdtool for mrtg + rrdtool
#
# (c) 1999,2000 bawidama@users.sourceforge.net
# (c) 2008      tobi@oetiker.ch (HW extension)
# (c) 2009      gvolk@gvolk.com (CSV export)

# use freely, but: NO WARRANTY - USE AT YOUR OWN RISK!

# if RRDs (rrdtool perl module) is not in the module search path (@INC)
# uncomment the following line and change the path appropriatly:
#use lib qw(/usr/local/rrdtool-1.0.33/lib/perl/ /usr/local/mrtg-2/lib/mrtg2/);
#use lib qw(/opt/rrdtool/lib64);

# RCS History - removed as it's available on the web
use lib qw(/usr/lib/mrtg2);

my $rcsid = '$Id: 14all.cgi,v 2.17 2002/02/07 21:37:08 rainer Exp $';
my $subversion = (split(/ /,$rcsid))[2];
$subversion =~ m/^\d+\.(\d+)$/;
my $version = "14all.cgi 1.1p$1";

# my $DEBUG = 0; has gone - use config "14all*GraphErrorsToBrowser: 1"

use strict;
use warnings;

use CGI;
BEGIN { eval { require CGI::Carp; import CGI::Carp qw/fatalsToBrowser/ }
	if $^O !~ m/Win/i };
use RRDs;
# use MRTG_lib "/usr/share/perl5/MRTG_lib.pm";
use MRTG_lib;

sub print_error($@);
sub intmax(@);
sub yesorno($);
sub get_graph_params($$$);
sub getdirwriteable($$);
sub getpngsize($);
sub errorpng();
sub gettextpic($);
sub log_rrdtool_call($$@);

my ($q, $cfgfile, $cfgfiledir);
my ($cgidir, @author, @style);

### where the mrtg.cfg file is
# anywhere in the filespace
#$cfgfile = '/home/mrtg/bin/mrtg.cfg';
# relative to the script
#$cfgfile = 'mrtg.cfg';
# use this so 14all.cgi gets the cfgfile name from the script name
# (14all.cgi -> 14all.cfg)
$cfgfile = '/etc/mrtg/mrtg.cfg';

# if you want to store your config files in a different place than your cgis:
$cfgfiledir = '/etc/mrtg';

$ENV{RRD_DEFAULT_FONT} = '/mrtg/fonts/opensans.ttf';
# $ENV{"TZ"} = "CST6CDT";


### customize the html pages
@author = ( -author => 'bawidama@users.sourceforge.net');
# one possibility to enable stylesheets (second is to use "AddHead[_]:..." in mrtg.cfg)
#@style = ( -style => { -src => 'general.css' });
###

if (!$cfgfile && $#ARGV == 0) {
	$cfgfile = shift @ARGV;
}

# initialize CGI
$q = new CGI;

# change for mrtg-2.9.*
my (@sorted, %config, %targets);
my %myrules = (
	'14all*errorpic' =>
		[sub{$_[0] && (-r $_[0] )}, sub{"14all*ErrorPic '$_[0]' not found/readable"}],
	'14all*grapherrorstobrowser' => [sub{1}, sub{"Internal Error"}],
	'14all*columns' =>
		[sub{int($_[0]) >= 1}, sub{"14all*Columns must be at least 1 (is '$_[0]')"}],
	'14all*rrdtoollog' =>
		[sub{$_[0] && (!-d $_[0] )}, sub{"14all*RRDToolLog must be a writable file"}],
	'14all*background' =>
		[sub{$_ =~ /^#[0-9a-f]{6}$/i}, sub{"14all*background colour not in form '#xxxxxx', x in [a-f0-9]"}],
	'14all*logarithmic[]' => [sub{1}, sub{"Internal Error"}],
	'14all*graphtotal[]' => [sub{1}, sub{"Internal Error"}],
	'14all*dontshowindexgraph[]' => [sub{1}, sub{"Internal Error"}],
	'14all*indexgraph[]' => [sub{1}, sub{"Internal Error"}],
	'14all*indexgraphsize[]' =>
		[sub{$_[0] =~ m/^\d+[,\s]+\d+$/o}, sub{"14all*indexgraphsize: need two numbers"}],
	'14all*maxrules[]' => [sub{1}, sub{"Internal Error"}],
);

my %graphparams = (
	'daily'   => ['-2000m', 'now',  300],
	'weekly'  => ['-12000m','now', 1800],
	'monthly' => ['-800h', 'now',  7200],
	'yearly'  => ['-400d', 'now', 86400],
	'daily.s' => ['-1250m', 'now',  300],
);

# look for the config file
my $meurl = $q->url(-relative => 1);
ensureSL(\$cfgfiledir);
if (defined $q->param('cfg')) {
	$cfgfile = $q->param('cfg');
	# security fix: don't allow ./ in the config file name
	print_error($q, "Illegal characters in cfg param: ./")
		if $cfgfile =~ m'(^/)|(\./)';
	$cfgfile = $cfgfiledir.$cfgfile unless -r $cfgfile;
	print_error($q, "Cannot find the given config file: \<tt>$cfgfile\</tt>")
		unless -r $cfgfile;
} elsif (!defined $cfgfile) {
	$cfgfile = $meurl;
	$cfgfile =~ s|.*\Q$MRTG_lib::SL\E||;
	$cfgfile =~ s/\.(cgi|pl|perl)$/.cfg/;
	#$meurl =~ m{\Q$MRTG_lib::SL\E([^\Q$MRTG_lib::SL\E]*)\.(cgi|pl)$};
	#$cfgfile = $1 . '.cfg';
	$cfgfile = $cfgfiledir.$cfgfile unless -r $cfgfile;
}

# read the config file

readcfg($cfgfile, \@sorted, \%config, \%targets, "14all", \%myrules);
my @processed_targets;
cfgcheck(\@sorted, \%config, \%targets, \@processed_targets);

# set some defaults
if (exists $config{refresh} && yesorno($config{refresh})
		&& $config{refresh} !~ m/^\d*[1-9]\d*$/o) {
	$config{refresh} = $config{interval} * 60;
}

my @headeropts = (@author, @style);

# the footer we print on every page
$config{icondir} ||= ''; # lets have a default for this
my $footer = <<"EOT" . $q->end_html;
<br/>
<br/>
<TABLE BORDER=0 CELLSPACING=0 CELLPADDING=0>
  <TR>
    <TD WIDTH=63><A ALT="MRTG"
    HREF="http://oss.oetiker.ch/mrtg"><IMG
    BORDER=0 SRC="$config{IconDir}mrtg-l.png"></A></TD>
    <TD WIDTH=25><A ALT=""
    HREF="http://oss.oetiker.ch/mrtg"><IMG
    BORDER=0 SRC="$config{IconDir}mrtg-m.png"></A></TD>
    <TD WIDTH=388><A ALT=""
    HREF="http://oss.oetiker.ch/mrtg"><IMG
    BORDER=0 SRC="$config{IconDir}mrtg-r.png"></A></TD>
  </TR>
</TABLE>
<TABLE BORDER=0 CELLSPACING=0 CELLPADDING=0>
  <TR VALIGN=top>
  <TD WIDTH=88 ALIGN=RIGHT><FONT FACE="Arial,Helvetica" SIZE=2>Version ${MRTG_lib::VERSION}</FONT></TD>
  <TD WIDTH=388 ALIGN=RIGHT><FONT FACE="Arial,Helvetica" SIZE=2>
  <A HREF="http://tobi.oetiker.ch">Tobias Oetiker</A>
  and
  <A HREF="http://www.bungi.com">Dave&nbsp;Rand</A>
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

### the main switch
# the modes:
# if parameter "dir" is given show a list of the targets in this "directory"
# elsif parameter "png" is given show a graphic for the target given w/ parameter "log"
# elsif parameter "log" is given show the page for this target
# elsif parameter "csv" is given send the data to the user as a CSV file transfer
# else show a list of directories and of targets w/o directory
# parameter "cfg" can hold the name of the config file to use
if (defined $q->param('dir')) {
	# show a list of targets in the given directory
	my $dir = $q->param('dir');
	my @httphead;
	push @httphead, (-expires => '+' . int($config{interval}) . 'm');
	if (yesorno($config{refresh})) {
		push @httphead, (-refresh => $config{refresh});
	}
	push @headeropts, (-bgcolor => ($config{'14all*background'} || '#ffffff'));
	my @htmlhead = (-title => "MRTG/RRD - Group $dir", @headeropts);
	#if ($targets{addhead}{_}) {
	#	push @htmlhead, (-head => $targets{addhead}{_});
	#}
	print $q->header(@httphead), $q->start_html(@htmlhead);
	print $q->h1("Available Targets"),"\n\<table width=100\%>\n";
	my $cfgstr = (defined $q->param('cfg') ? "&cfg=".$q->param('cfg') : '');
	my $column = 0;
	my $pngdir = getdirwriteable($config{imagedir},$dir);
	my $confcolumns = $config{'14all*columns'} || 2;
	foreach my $tar (@sorted) {
		my $small = 0;
		my $descr = 0;
		unless (yesorno($targets{'14all*dontshowindexgraph'}{$tar})) {
			$small = $targets{'14all*indexgraph'}{$tar};
			$small = 'daily.s' unless $small;
		}
		next if $tar =~ m/^[\$\^\_]$/; # _ is not a real target
		next if $targets{directory}{$tar} ne $dir;
		$descr = $targets{pagetop}{$tar}; ###GVOLK
	#system("/bin/echo", $descr);
		#print "system "/bin/echo $descr"";

#system "/bin/echo \" $pager_name \n\r $pretty_number\" | /bin/mail $pager_email 2>&1";

		print '<tr>' if $column == 0;
		print '<td>',
			$q->br($q->a({href => "$meurl?log=$tar$cfgstr"}, $targets{title}{$tar}));   ###GVOLK
			#$q->p($q->a({href => "$meurl?log=$tar$cfgstr"}, $targets{title}{$tar}));   ###GVOLK
		#print '<p>'; ###GVOLK - 2010-12-29
		print $q->a({href => "$meurl?log=$tar$cfgstr"},
			$q->img({src => "$meurl?log=$tar&png=$small&small=1$cfgstr",
				alt => "index-graph",
				getpngsize("$pngdir$tar-$small-i.png")})
			) if $small;
		print "\</td>\n";
		$column++;
		if ($column >= $confcolumns) {
			$column = 0;
			print '</tr>';
		} 
		#print '<p>';
	}
	if ($column != 0 and $column < $confcolumns) {
		print '<td>&nbsp;</td>' x ($confcolumns - $column),"\</tr>\n";
	}
	print '</table>', $footer;
} elsif (defined $q->param('png')) {
	# send a graphic, create it if necessary
	my $errstr = '';
	if (!defined $q->param('log')) {
		$errstr="CGI call error: missing param 'log'";
		goto ERROR;
	}
	my $png = $q->param('png');
	my $log = $q->param('log');
	unless (exists $targets{target}{$log}) {
		$errstr="target '$log' unknown";
		goto ERROR;
	}
	# fix a problem with indexmaker
	if (defined $q->param('small')) {
		my %imaker = qw/day.s daily.s week.s weekly month.s monthly year.s yearly/;
		if (exists $imaker{$png}) {
			$png = $imaker{$png};
		}
	}
	my ($start, $end, $maxage);
	my $graphparams = $targets{"graph*$png"}{$log};
	if ($graphparams) {
		($start, $end, $maxage) = split(/[,\s]+/, $graphparams, 3);
	}
	unless ($start && $end && $maxage) {
		unless (exists $graphparams{$png}) {
			$errstr="CGI call error: graph '$png' unknown";
			goto ERROR;
		}
		($start, $end, $maxage) = @{$graphparams{$png}};
	}
	my ($xs, $ys);
	if (defined $q->param('small')) {
		($xs, $ys) = (250, 100);
		($xs, $ys) = ($targets{'14all*indexgraphsize'}{$log} =~ m/\d+[,\s]+\d+/)
			if $targets{'14all*indexgraphsize'}{$log};
	} else {
		($xs, $ys) = ($targets{xsize}{$log}, $targets{ysize}{$log});
	}
	unless ($xs && $ys) {
		$errstr="cannot get image sizes for graph $png / target $log";
		goto ERROR;
	}
	my $rrd = $config{logdir}.$targets{directory}{$log} . $log . '.rrd';
	# escape ':' and '\' with \ in $rrd
	# (rrdtool replaces '\:' by ':' and '\\' by '\')
	$rrd =~ s/([:\\])/\\$1/g;
	my $pngdir = getdirwriteable($config{imagedir}, $targets{directory}{$log});
	$png .= '-i' if defined $q->param('small');
	my $pngfile = "${pngdir}${log}-${png}.png";
	
	# build the rrd command line: set the starttime and the graphics format (PNG)
	my @args = ($pngfile, '-s', $start, '-e', $end, '-a', 'PNG');
	# if it's not a small picture set the legends
	my ($l1,$l2,$l3,$l4,$li,$lo) = ('','','','','','');
	my ($ri, $ro) = ('','');

	push @args, '-w', $xs, '-h', $ys;
	if (!defined $q->param('small')) {
		foreach (qw/legend1 legend2 legend3 legend4 legendi legendo legendy shortlegend/) {
			if ($targets{$_}{$log}) {
				$targets{$_}{$log} =~ s'&nbsp;' 'go; #'
				$targets{$_}{$log} =~ s/%/%%/go;
			}
		}
		my $persec = $targets{options}{bits}{$log} ? 'Bits' : 'Bytes';
		if ($targets{ylegend}{$log}) {
			push @args, '-v', $targets{ylegend}{$log}; }

		if ($targets{legend1}{$log}) {
			$l1 = ":".$targets{legend1}{$log}."\\l"; }
		else {
			$l1 = ":Incoming Traffic in $persec per Second\\l"; }
		if ($targets{legend2}{$log}) {
			$l2 = ":".$targets{legend2}{$log}."\\l"; }
		else {
			$l2 = ":Outgoing Traffic in $persec per Second\\l"; }
		if ($targets{legend3}{$log}) {
			$l3 = ":".$targets{legend3}{$log}."\\l"; }
		else {
			$l3 = ":Maximal 5 Minute Incoming Traffic\\l"; }
		if ($targets{legend4}{$log}) {
			$l4 = ":".$targets{legend4}{$log}."\\l"; }
		else {
			$l4 = ":Maximal 5 Minute Outgoing Traffic\\l"; }

		if (exists $targets{legendi}{$log}) {
			$li = $targets{legendi}{$log}; }
		else {	$li = "In: "; }
		$li =~ s':'\\:'; # ' quote :
		if (exists $targets{legendo}{$log}) {
			$lo = $targets{legendo}{$log}; }
		else {	$lo = "Out:"; }
		$lo =~ s':'\\:'; # ' quote :

		if ($targets{options}{integer}{$log}) {
			$li .= ' %9.0lf';
			$lo .= ' %9.0lf';
			$ri = '%3.0lf%%';
			$ro = '%3.0lf%%';
		} else {
			$li .= ' %8.3lf';
			$lo .= ' %8.3lf';
			$ri = '%6.2lf%%';
			$ro = '%6.2lf%%';
		}
		if (!defined($targets{kmg}{$log}) || $targets{kmg}{$log}) {
			$li .= ' %s';
			$lo .= ' %s';
			if ($targets{kilo}{$log}) {
				push @args, '-b', $targets{kilo}{$log};
			}
			if ($targets{shortlegend}{$log}) {
				$li .= $targets{shortlegend}{$log};
				$lo .= $targets{shortlegend}{$log};
			}
		}
	}
	my $factor = 1; # should we scale the values?
	if ($targets{options}{perminute}{$log}) {
		$factor = 60; # perminute -> 60x
	} elsif ($targets{options}{perhour}{$log}) {
		$factor = 3600; # perhour -> 3600x
	}
	if ($targets{options}{bits}{$log}) {
		$factor *= 8; # bits instead of bytes -> 8x
	}
	# let the user give an arbitrary factor:
	if ($targets{factor}{$log} and
		$targets{factor}{$log} =~ m/^[-+]?\d+(.\d+)?([eE][+-]?\d+)?$/)
	{
		$factor *= 0+$targets{factor}{$log};
	}
	my $pngchar = substr($png,0,1);
	if ($pngchar and $targets{unscaled}{$log} and
		   $targets{unscaled}{$log} =~ m/$pngchar/) {
		my $max = intmax($targets{maxbytes}{$log},
			$targets{maxbytes1}{$log},
			$targets{maxbytes2}{$log},
			$targets{absmax}{$log});
		$max *= $factor;
		push @args, '-l', 0, '-u', $max, '-r';
	} elsif (yesorno($targets{'14all*logarithmic'}{$log})) {
		push @args, '-o';
	}
	push @args,'--alt-y-grid','--lazy','-c','MGRID#ee0000','-c','GRID#000000';
	# now build the graph calculation commands
	# ds0/ds1 hold the normal data sources to graph/gprint
	my ($ds0, $ds1) = ('in', 'out');
	push @args, "DEF:$ds0=$rrd:ds0:AVERAGE", "DEF:$ds1=$rrd:ds1:AVERAGE";
	if (defined $targets{options}{unknaszero}{$log}) {
		push @args, "CDEF:uin=$ds0,UN,0,$ds0,IF",
			"CDEF:uout=$ds1,UN,0,$ds1,IF";
		($ds0, $ds1) = ('uin', 'uout');
	}
	if ($factor != 1) {
		# scale the values. we need a CDEF for this
		push @args, "CDEF:fin=$ds0,$factor,*","CDEF:fout=$ds1,$factor,*";
		($ds0, $ds1) = ('fin', 'fout');
	}
	my $maximum0 = $targets{maxbytes1}{$log} || $targets{maxbytes}{$log};
	my $maximum1 = $targets{maxbytes2}{$log} || $targets{maxbytes}{$log};
	$maximum0 = 1 unless $maximum0;
	$maximum1 = 1 unless $maximum1;
	# ps0/ps1 hold the percentage data source for gprint
	my ($ps0, $ps1) = ('pin', 'pout');
	push @args, "CDEF:pin=$ds0,$maximum0,/,100,*,$factor,/",
		"CDEF:pout=$ds1,$maximum1,/,100,*,$factor,/";

	if (yesorno($targets{'14all*graphtotal'}{$log})
			&& defined $q->param('small')) {
		push @args, "CDEF:total=$ds0,$ds1,+", "LINE1:total#ffa050:Total AVG\\l";
	}
	# now for the peak graphs / maximum values
	# mx0/mx1 hold the maximum data source for graph/gprint
	my ($mx0, $mx1) = ($ds0, $ds1);
	# px0/px1 hold the maximum pecentage data source for gprint
	my ($px0, $px1) = ($ps0, $ps1);
	if (!defined $q->param('small')) {
		# the defs for the maximum values: for the legend ('MAX') and probabely
		# for the 'withpeak' graphs
		push @args, "DEF:min=$rrd:ds0:MAX", "DEF:mout=$rrd:ds1:MAX";
		($mx0, $mx1) = ('min', 'mout');
		if (defined $targets{options}{unknaszero}{$log}) {
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
		if ($targets{withpeak}{$log} &&
				substr($png,0,1) =~ /[$targets{withpeak}{$log} ]/) {
			push @args, (defined $targets{rrdhwrras}{$log} ? "LINE1" : "AREA" ).':'.$mx0.$targets{rgb3}{$log}.$l3,
				"LINE1:".$mx1.$targets{rgb4}{$log}.$l4;
			push @args, "CDEF:pmin=$mx0,$maximum0,/,100,*,$factor,/",
				"CDEF:pmout=$mx1,$maximum1,/,100,*,$factor,/";
			($px0, $px1) = ('pmin', 'pmout');
			if (yesorno($targets{'14all*graphtotal'}{$log})) {
				push @args, "CDEF:mtotal=$mx0,$mx1,+", "LINE1:mtotal#ff5050:Total MAX\\l";
			}
		}
	}
	# the commands to draw the values
	my (@hr1, @hr2);
	if (!defined $q->param('small') && yesorno($targets{'14all*maxrules'}{$log})) {
		chop $l1; chop $l1; chop $l2; chop $l2;
		@hr1 = (sprintf("HRULE:%d#ff4400: MaxBytes1\\l",$maximum0*$factor));
		@hr2 = (sprintf("HRULE:%d#aa0000: MaxBytes2\\l",$maximum1*$factor));
	}
        
	push @args, (defined $targets{rrdhwrras}{$log} ? "LINE1" : "AREA" ).':'.$ds0.$targets{rgb1}{$log}.$l1, @hr1,
  		    "LINE1:".$ds1.$targets{rgb2}{$log}.$l2, @hr2;
	if (!defined $q->param('small')) {
                # draw confidence band if rrdhwrras are enabled
                if (defined $targets{rrdhwrras}{$log}){
                        push @args, 
                          "DEF:pred0=${rrd}:ds0:HWPREDICT",
                          "DEF:pred1=${rrd}:ds1:HWPREDICT",
                          "DEF:dev0=${rrd}:ds0:DEVPREDICT",
                          "DEF:dev1=${rrd}:ds1:DEVPREDICT",
                          "DEF:fail0=${rrd}:ds0:FAILURES",
                          "DEF:fail1=${rrd}:ds1:FAILURES",
			  "TICK:fail0$targets{rgb1}{$log}:1.0",
			  "TICK:fail1$targets{rgb2}{$log}:1.0",
                          "CDEF:hwwidth0=dev0,4,*,${factor},*",
                          "CDEF:hwwidth1=dev1,4,*,${factor},*",
                          "CDEF:hwlower0=pred0,dev0,2,*,-,${factor},*",
                          "CDEF:hwlower1=pred1,dev1,2,*,-,${factor},*",
                          "LINE1:hwlower0$targets{rgb1}{$log}40","AREA:hwwidth0$targets{rgb1}{$log}60::STACK","LINE1:0$targets{rgb1}{$log}40::STACK",
                          "LINE1:hwlower1$targets{rgb2}{$log}40","AREA:hwwidth1$targets{rgb2}{$log}40::STACK","LINE1:0$targets{rgb2}{$log}90::STACK"
                }
		# print the legends
		if ($targets{options}{nopercent}{$log}) {
			push @args,
				"GPRINT:$mx0:MAX:Max $li",
				"GPRINT:$mx1:MAX:Max $lo\\l",
				"GPRINT:$ds0:AVERAGE:Avg $li",
				"GPRINT:$ds1:AVERAGE:Avg $lo\\l",
				"GPRINT:$ds0:LAST:Cur $li",
				"GPRINT:$ds1:LAST:Cur $lo\\l";
		} else {
			push @args,
				"GPRINT:$mx0:MAX:Max $li",
				"GPRINT:$px0:MAX:($ri)",
				"GPRINT:$mx1:MAX:Max $lo",
				"GPRINT:$px1:MAX:($ro)\\l",
				"GPRINT:$ds0:AVERAGE:Avg $li",
				"GPRINT:$ps0:AVERAGE:($ri)",
				"GPRINT:$ds1:AVERAGE:Avg $lo",
				"GPRINT:$ps1:AVERAGE:($ro)\\l",
				"GPRINT:$ds0:LAST:Cur $li",
				"GPRINT:$ps0:LAST:($ri)",
				"GPRINT:$ds1:LAST:Cur $lo",
				"GPRINT:$ps1:LAST:($ro)\\l";
		}
	}
	# fire up rrdtool
	my ($a, $rrdx, $rrdy) = RRDs::graph(@args);
	my $e = RRDs::error();
	log_rrdtool_call($config{'14all*rrdtoollog'},$e,'graph',@args);
	if ($e) {
		if (!-w $pngdir) {
			$errstr = "cannot write to graph dir $pngdir\nrrdtool error: $e";
		} elsif (-e $pngfile and !-w _) {
			$errstr = "cannot write $pngfile\nrrdtool error: $e";
		} elsif (-e $pngfile) {
			if (unlink($pngfile)) {
				# try rrdtool a second time
				($a, $rrdx, $rrdy) = RRDs::graph(@args);
				$e = RRDs::error();
				log_rrdtool_call($config{'14all*rrdtoollog'},$e,'graph',@args);
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
			print $q->header(-type => "image/png", -expires => "+${maxage}s");
			binmode(PNG); binmode(STDOUT);
			while(read PNG, my $buf, 16384) { print STDOUT $buf; }
			close PNG;
			exit 0;
		}
		$errstr = "cannot read graph file: $!";
	}
	ERROR:
	if (yesorno($config{'14all*grapherrorstobrowser'})) {
		my ($errpic, $format) = gettextpic($errstr);
		print $q->header(-type => $format, -expires => 'now');
		binmode(STDOUT);
		print $errpic;
		exit 0;
	}
	$log ||= '_';
	if (defined $targets{options}{'14all*errorpic'}{$log} &&
			open(PNG, $targets{options}{'14all*errorpic'}{$log})) {
		print $q->header(-type => "image/png", -expires => 'now');
		binmode(PNG); binmode(STDOUT);
		while(read PNG, my $buf,16384) { print STDOUT $buf; }
		close PNG;
		exit 0;
	}
	print $q->header(-type => "image/png", -expires => 'now');
	binmode(STDOUT);
	print pack("C*", errorpng());
	exit 0;
} elsif (defined $q->param('log')) {
	# show the graphics for one target
	my $log = $q->param('log');
	print_error($q,"Target '$log' unknown") if (!exists $targets{target}{$log});
	my $title;
	# user defined title?
	if ($targets{title}{$log}) {
		$title = $targets{title}{$log};
	} else {
		$title = "MRTG/RRD - Target $log";
	}
	my @httphead;
	push @httphead, (-expires => '+' . int($config{interval}) . 'm');
	if (yesorno($config{refresh})) {
		push @httphead, (-refresh => $config{refresh});
	}
	my @htmlhead = (-title => $title, @headeropts,
		-bgcolor => $targets{background}{$log});
	if ($targets{addhead}{$log}) {
		push @htmlhead, (-head => $targets{addhead}{$log});
	}
	print $q->header(@httphead), $q->start_html(@htmlhead);
	# user defined header line? (should exist as mrtg requires it)
	print $targets{pagetop}{$log},"\n";
	my $rrd = $config{logdir}.$targets{directory}{$log} . $log . '.rrd';
	my $lasttime = RRDs::last($rrd);
	my $date = `date \cut -d" " -f5`;
	log_rrdtool_call($config{'14all*rrdtoollog'},'','last',$rrd);

	my $cfgstr = (defined $q->param('cfg') ? "&cfg=".$q->param('cfg') : '');
	my $rrdstr = (defined $q->param('log') ? "&rrd=".$q->param('log').".rrd" : '');

	print $q->hr,
		"The statistics were last updated(Timezone = CST/CDT): ",$q->b(scalar(localtime($lasttime))),
		$q->hr if $lasttime ;
	my $sup = $targets{suppress}{$log} || '';
	my $url = "$meurl?log=$log";
        my $exporturl = "rrd-export.cgi?log=$log";
	my $tmpcfg = $q->param('cfg');
	$url .= "&cfg=$tmpcfg" if defined $tmpcfg;
	$url .= "&png";

        my $factorstr="&fact=1";

        if ($targets{options}{bits}{$log}) {
          $factorstr = "&fact=8"; # bits instead of bytes -> 8x
        } 
        if ($targets{options}{perminute}{$log}) {
          $factorstr = "&fact=60"; # perminute -> 60x
        } 
        if ($targets{options}{perhour}{$log}) {
          $factorstr = "&fact=3600"; # perhour -> 3600
        } 

	# the header lines and tags for the graphics
	my $pngdir = getdirwriteable($config{imagedir}, $targets{directory}{$log});
        my $cfstr;
        my $rangestr;
	if ($sup !~ /d/) {
		print $q->h2("'Daily' graph (5 Minute Average)"),"\n",
			$q->img({src => "$url=daily", alt => "daily-graph",
				getpngsize("$pngdir$log-daily.png")}
			), "\n";

	   # vvvvv   Added for CSV output links (see 2009-02-27 note below)
           $cfstr="&cf=AVERAGE";
           $rangestr="&range=240000";

           print $q->td($q->a({href => "$meurl?&csv=1$rrdstr$cfgstr$cfstr$rangestr$factorstr"})),"\n";
           print "<br>CSV Export (Last 64 Hours, 5 Minute Average)\n";
           print "</a>";
	   # ^^^^^   Added for CSV output links (see 2009-02-27 note below)
	}


	if ($sup !~ /w/) {
		print $q->h2("'Weekly' graph (30 Minute Average)"),"\n",
			$q->img({src => "$url=weekly", alt => "weekly-graph",
				getpngsize("$pngdir$log-weekly.png")}
			), "\n";

	   # vvvvv   Added for CSV output links (see 2009-02-27 note below)
           $cfstr="&cf=AVERAGE";
           $rangestr="&range=1440000";
           print $q->td($q->a({href => "$meurl?&csv=1$rrdstr$cfgstr$cfstr$rangestr$factorstr"})),"\n";
           print "<br>CSV Export (Last 16 Days, 30 Minute Average)\n";
           print "</a>";
 
           $cfstr="&cf=MAX";
           $rangestr="&range=1440000";
           print $q->td($q->a({href => "$meurl?&csv=1$rrdstr$cfgstr$cfstr$rangestr$factorstr"})),"\n";
           print "<br>CSV Export (Last 16 Days, 30 Minute Maximum)\n";
           print "</a>";
	   # ^^^^^   Added for CSV output links (see 2009-02-27 note below)
	}



	if ($sup !~ /m/) {
		print $q->h2("'Monthly' graph (2 Hour Average)"),"\n",
			$q->img({src => "$url=monthly", alt => "monthly-graph",
				getpngsize("$pngdir$log-monthly.png")}
			), "\n";
	   # vvvvv   Added for CSV output links (see 2009-02-27 note below)
           $cfstr="&cf=AVERAGE";
           $rangestr="&range=5760000";
           print $q->td($q->a({href => "$meurl?&csv=1$rrdstr$cfgstr$cfstr$rangestr$factorstr"})),"\n";
           print "<br>CSV Export (Last 64 Days, 2 Hour Average)\n";
           print "</a>";

           $cfstr="&cf=MAX";
           $rangestr="&range=5760000";
           print $q->td($q->a({href => "$meurl?&csv=1$rrdstr$cfgstr$cfstr$rangestr$factorstr"})),"\n";
           print "<br>CSV Export (Last 64 Days, 2 Hour Maximum)\n";
           print "</a>";
	   # ^^^^^   Added for CSV output links (see 2009-02-27 note below)
	}




	if ($sup !~ /y/) {
		print $q->h2("'Yearly' graph (1 Day Average)"),"\n",
			$q->img({src => "$url=yearly", alt => "yearly-graph",
				getpngsize("$pngdir$log-yearly.png")}
			), "\n";

	   # vvvvv   Added for CSV output links (see 2009-02-27 note below)
           $cfstr="&cf=AVERAGE";
           $rangestr="&range=69120000";
           print $q->td($q->a({href => "$meurl?&csv=1$rrdstr$cfgstr$cfstr$rangestr$factorstr"})),"\n";
           print "<br>CSV Export (Last 800 days, 24 Hour Average)\n";
           print "</a>";

           $cfstr="&cf=MAX";
           $rangestr="&range=69120000";
           print $q->td($q->a({href => "$meurl?&csv=1$rrdstr$cfgstr$cfstr$rangestr$factorstr"})),"\n";
           print "<br>CSV Export (Last 800 days, 24 Hour Maximum)\n";
           print "</a>";
	   # ^^^^   Added for CSV output links (see 2009-02-27 note below)
	}


	if ($targets{pagefoot}{$log}) {
		print $targets{pagefoot}{$log};
	}
	print $footer;

} elsif (defined $q->param('csv')) {   # execute this if ?csv parm is set
	# This was added 2009-02-27 by Greg Volk <gvolk@gvolk.com>
	# If csv parm is passed to 14all.cgi, give the user the data as a 
        # csv file.
	# Additional CSV related parms to 14all.cgi are:
	# 	cf - consolidation factor
	#	range - how far to go back for return data
	#	fact - multiplicative factor (set to 8 for bytes to bits
	#	rrd - what rrdfile
	#	iso8601 - return time in iso8601 format (2009-02-27 15:05)
	#
	# A sample call using all the options looks like:
	# http://myserver/cgi-bin/14all.cgi?&csv=1&rrd=myrouter_fastethernet_10.rrd&cfg=myrouter.cfg&cf=AVERAGE&range=1260000&fact=8&iso8601=1
	#
	# A call using the minimum options for csv output looks like:
	# http://myserver/cgi-bin/14all.cgi?&csv=1&rrd=myrouter_fastethernet_10.rrd&cfg=myrouter.cfg
	#

	# Hash our month names so we can output in ISO8610 time format (why 
	# is ISO8601 time output not builtin to perl? Or is it now?
	my %month = ( 	"Jan" => "01",
			"Feb" => "02",
			"Mar" => "03",
			"Apr" => "04",
			"May" => "05",
			"Jun" => "06",
			"Jul" => "07",
			"Aug" => "08",
			"Sep" => "09",
			"Oct" => "10",
			"Nov" => "11",
			"Dec" => "12"   );

	# Declare some vars       
	my @httphead;
        my @csvdata;
	push @httphead, (-expires => 'now');    # don't cache this stuff
        my $rrd = $q->param('rrd'); 

        my $basedir = $config{logdir};		# find WorkDir in the cfg file
        my $cf  = $q->param('cf');
        my $range = $q->param('range');	
        my $factor = $q->param('fact');	
        my $iso8601 = $q->param('iso8601');
        my $end = $q->param('end');
        my $tar = $rrd;	#target name = rrd filename without .rrd on it

	my ($dir,$ds0name,$ds1name,$element,$time,$yyyy,$mm,$dd,$hour,
	    $min,$sec,@array,$lt,$hhmmss);

        print_error($q, "Illegal characters in rrd param: ./") if $rrd =~ m'(^/)|(\./)';

        $tar =~ s/\.rrd//g;			# remove ".rrd" from targetname

        $dir = $targets{directory}{$tar};	# what subdir are we looking in?
        if ($targets{legendi}{$tar}) {		# if legendi and legendo are defined in cfg
          $ds0name = $targets{legendi}{$tar};   # file, use those for the csv output labels
        } else {
          $ds0name = "input";			# udderwise, use the standard input/output
        }
        if ($targets{legendo}{$tar}) {
          $ds1name = $targets{legendo}{$tar};
        } else {
          $ds1name = "output";
        }

        unless ($cf) { $cf = "AVERAGE"; }	# if &cf is not defined, assume AVERAGE
        unless ($factor) { $factor = 1; }	# if &factor is not defined, assume 1
        unless ($range) { $range = "240000"; }	# if &range is not defined, assume 48 hours
        unless ($end) { $end = "now"; }

        my $rrdfile = "$basedir/$dir/$rrd";	# full path to rrdfile
        my $csvfile = $rrd;			# csv filename
        $csvfile =~ s/\.rrd/\.csv/g;		# replace .rrd with .csv in filename

        #print "basedir = $basedir dir = $dir rrd = $rrd<br>"; # debug
        #print "full path to rrdfile = $basedir/$dir/$rrd\n";  # debug


	# Get some data, or pointers to data out of the RRD file
	my ($start,$step,$names,$data) = RRDs::fetch $rrdfile, $cf, "-s -$range", "-e $end";

  	my $ERR = RRDs::error;  # Trap RRD read errors (we'll print below if necessary)


        # Iterate over each data point in @$data
        foreach $element (@$data) {
          # Increment the time by the step value
          $time += $step;

          $lt = localtime($start+$time);

	  # Convert to ISO8601 time if &iso8601 is set
	  if($iso8601) {
	    # Convert to ISO8601
	    @array = split /\s+/,$lt;
	    $yyyy = $array[4];
	    $mm = $month{$array[1]};
	    $dd = $array[2];

	    # We want two digit days, turn "9" into "09"
	    if((length $dd) < 2) { $dd = "0".$dd; }
       
	    $hhmmss = $array[3];
	    @array = split ":",$hhmmss;
            $hour = $array[0];
	    $min = $array[1];
	    $sec = $array[2];
	    $lt = "$yyyy-$mm-$dd $hour:$min:$sec";
          }
        
	  # Store the values in @csvdata 
	  push(@csvdata,$lt.",".$$element[0]*$factor.",".$$element[1]*$factor."\n");
        }

	# Tell the http client what to expect
        print "Content-Type:application/x-download\n";  
        print "Content-Disposition:attachment;filename=$csvfile\n\n";

	# Let the client know if RRDs::fetch returned an error
  	print "Error while reading $rrdfile: $ERR\n" if $ERR;

        # Print the data with a header
	print "date_time,$ds0name,$ds1name\n";
        print @csvdata;

	### End of 2009-02-27 mod for csv output

} else {
	# no parameter - show a list of directories and targets without "Directory[...]" (aka root-targets)
	my @httphead;
	push @httphead, (-expires => '+1d'); # how often do you add targets?
	if (yesorno($config{refresh})) {
		push @httphead, (-refresh => $config{refresh});
	}
	push @headeropts, (-bgcolor => ($config{'14all*background'} || '#ffffff'));
	my @htmlhead = (-title => "MRTG/RRD $version", @headeropts);
	#if ($targets{addhead}{_}) {
	#	push @htmlhead, (-head => $targets{addhead}{_});
	#}
	print $q->header(@httphead), $q->start_html(@htmlhead);
	my (@dirs, %dirs, @logs);
	# get the list of directories and "root"-targets
	foreach my $tar (@sorted) {
		next if $tar =~ m/^[_\$\^]$/; # pseudo targets
		if ($targets{directory}{$tar}) {
			next if exists $dirs{$targets{directory}{$tar}};
			$dirs{$targets{directory}{$tar}} = $tar;
			push @dirs, $targets{directory}{$tar};
		} else {
			push @logs, $tar;
		}
	}
	my $cfgstr = (defined $q->param('cfg') ? "&cfg=".$q->param('cfg') : '');
	print $q->h1("Available Targets"),"\n";
	my $confcolumns = $config{'14all*columns'} || 2;
	if ($#dirs > -1) {
		print $q->h2("Directories"),"\n\<table width=100\%>\n";
		my $column = 0;
		foreach my $tar (@dirs) {
			print '<tr>' if $column == 0;
			(my $link = $tar) =~ s/ /\+/g;
			chop $tar; # remove / for display (from ensureSL)
			print $q->td($q->a({href => "$meurl?dir=$link$cfgstr"},
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
	if ($#logs > -1) {
		print $q->h2("Targets"),"\n\<table width=100\%>\n";
		my $column = 0;
		foreach my $tar (@logs) {
			my $small = 0;
			unless (yesorno($targets{'14all*dontshowindexgraph'}{$tar})) {
				$small = $targets{'14all*indexgraph'}{$tar};
				$small = 'daily.s' unless $small;
			}
			next if $tar =~ m/^[\$\^_]$/;
			print '<tr>' if $column == 0;
			print '<td>',
				$q->p($q->a({href => "$meurl?log=$tar$cfgstr"},$targets{title}{$tar}));
			print $q->a({href => "$meurl?log=$tar$cfgstr"},
				$q->img({src => "$meurl?log=$tar&png=$small&small=1$cfgstr",
					alt => "index-graph",
					getpngsize(getdirwriteable($config{imagedir},'')."$tar-$small-i.png")}))
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
	print $footer;
}
exit 0;

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
	my $fh = IO::File->new;
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
		my $im = new GD::Image($xs + 20, $ys + 20);
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
	my $logfile = shift;
	my $error = shift;
	return unless yesorno($logfile);
	unless (open(LOG, '>>'.$logfile)) {
		print STDERR "cannot log rrdtool call: $!\n";
		return;
	}
	print LOG "\n# call to rrdtool:\nrrdtool @_\n";
	if ($error) {
		print LOG "# gave ERROR: $error\n";
	} else {
		print LOG "# completed without error\n";
	}
	close LOG;
}
