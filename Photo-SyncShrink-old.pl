#!/usr/bin/perl
# pl -> exe
# pp -o genMUS-Config-RCS-RES.exe genMUS-Config-RCS-RES.pl
#-M Thread::Queue
#-a "source;target"

# REQUIRES
# Image Magick und Perl Magick installiert

# DONE
# - Foreach filesIn not in filesOut
# - Vergleich Liste Dateien Ordner In / Out -> ggf unter Out löschen

# TODO
# - Ordner prüfen / anlegen (encoding, OS-unabhängig)
# - Löschen von alten Ordnern
# - Convert via Image Magick
# - Convert via multi threading
# Beachten
# - Encoding von Dateiname? -> nur bei Ausgaben relevant
# IGNORE
# - FileIn modifiziert, keine Updates, nur neue Dateien werden exportiert
# V2
# - Config Datei oder Parameter
# - unter Out leere Verz löschen
# - Ausgabe: nur Dateiname, Order nur einmal

# - Ordner Nackidei nicht!

use strict;
use warnings;
use v5.10;    # say
use Data::Dumper;

use File::Path;    # rmtree

use File::Path qw(make_path);    # for make_path("dir1/dir2");
use File::Basename;              # for fileparse $file -> $fpath, $fname, $fext
use Encode;
# use Encode::Guess qw/utf8 cp1252/; # latin1

# use Image::Resize; # alternative zu ImageMagick, hatte aber keine brauchbaren Bilder erzeugt.
# use Image::Magick; # hatte Probleme das Perl Modul zu kompilieren, daher einfach ImageMagick convert direkt aufgerufen

use threads;
use Thread::Queue;
my $numThreads = 2;

# Preparing Threads
# my $q = new Thread::Queue;
# my @Threads = ();

my $blacklist = join '|', qw (
    150613
);

my $os;
if    ( $^O eq 'MSWin32' ) { $os = 'win'; }
elsif ( $^O eq 'linux' )   { $os = 'lin'; }
else                       { die "unknown OS: $^O\n"; }

my $maxsize              = 1920;
my $jpg_compress_quality = 75;
my $removeExif           = 0;      # ggf nicht, damit Datum und Ort erhalten bleiben

my $copyVideoFiles      = 0;
my @extVideos           = qw(avi mp4 mov mkv);
my $copyNonPictureFiles = 0;
my @filesIgnore         = qw(Thumbs.db);

my $copyNackideis = 0;

my $convertPara = "-auto-orient ";
if ( $jpg_compress_quality > 0 ) { $convertPara .= "-quality $jpg_compress_quality " }
if ( $removeExif )               { $convertPara .= "-strip " }
if ( $maxsize > 0 )              { $convertPara .= "-size " . $maxsize . "x" . $maxsize . " -resize " . $maxsize . "x" . $maxsize . "\\\> " }

my $decodingIn  = "utf-8";
my $decodingOut = "utf-8";

if ( $os eq 'win' ) {
  $decodingIn  = "latin1";
  $decodingOut = "cp850";
  $convertPara =~ s#\\>#^>#;    # > is a special char, in Linux we use \> and in Windows ^>
}

# for my $jahr (qw(2008_2_Dresden 2009 2010 2011 2012 2013 2014 2015 2016 2017 2018)) {
# TODO: Schleife über Jahre tut nicht, vermutlich weil dirIn in Sub verwendet werden :-(
my $jahr  = $ARGV[ 0 ];
my $dirIn = 'F:/FotoalbumSSD/Jahre/' . $jahr;
die "E: No folder named '$jahr' found" if not -d "$dirIn";

{    #
  # Reset thread stuff
  my $q       = new Thread::Queue;
  my @Threads = ();

  my $dirOut = 'E:/Dropbox/Fotos/FotoalbumSync1920/' . $jahr;
  mkdir $dirOut unless -d $dirOut;

  # # TODO
  # $dirIn  = 'e:/tmp/source';
  # $dirOut = 'e:/tmp/target-PL';

  # CleanUp Out #1: remove dirs missing in In from Out
  my @listDirsDirIn  = traverseDirGetDirs( $dirIn );
  my @listDirsDirOut = traverseDirGetDirs( $dirOut );
  # trim base path for comparision of lists
  @listDirsDirIn  = map { s#^$dirIn/##;  $_ } @listDirsDirIn;
  @listDirsDirOut = map { s#^$dirOut/##; $_ } @listDirsDirOut;
  my @listOldOutputDirsToDelete = arrayMinus( \@listDirsDirOut, \@listDirsDirIn );
  @listOldOutputDirsToDelete = map {"$dirOut/$_"} @listOldOutputDirsToDelete;
  undef @listDirsDirIn;
  undef @listDirsDirOut;
  # print Dumper @listOldOutputDirsToDelete and die;
  foreach my $dir ( reverse @listOldOutputDirsToDelete ) {
    say "'deleting $dir'";
    rmtree $dir or die $!;
  }
  undef @listOldOutputDirsToDelete;

  # CleanUp Out #2: remove files missing in In from Out
  my @listFilesDirIn = traverseDirGetFiles( $dirIn );

  if ( $copyNackideis != 1 ) {
    @listFilesDirIn = grep { not m/\/Nackidei/i } @listFilesDirIn;
  }

  @listFilesDirIn = grep { not m/\/($blacklist) /i } @listFilesDirIn;

  my @listFilesDirOut = traverseDirGetFiles( $dirOut );
  # remove base path for comparision of lists
  @listFilesDirIn  = map { s#^$dirIn/##;  $_ } @listFilesDirIn;
  @listFilesDirOut = map { s#^$dirOut/##; $_ } @listFilesDirOut;
  my @listToExport               = arrayMinus( \@listFilesDirIn,  \@listFilesDirOut );
  my @listOldOutputFilesToDelete = arrayMinus( \@listFilesDirOut, \@listFilesDirIn );
  undef @listFilesDirIn;
  undef @listFilesDirOut;
  @listToExport               = map {"$dirIn/$_"} @listToExport;
  @listOldOutputFilesToDelete = map {"$dirOut/$_"} @listOldOutputFilesToDelete;
  # Löschen von listFilesDirOut wenn nicht in listFilesDirIn
  foreach my $file ( @listOldOutputFilesToDelete ) {
    say "'deleting $file'";
    unlink $file or die $!;
  }
  undef @listOldOutputFilesToDelete;

  # say Dumper @listToExport;

  # convert via ImageMagick via Treads

  # the work to be done for all items of thread queue
  sub tsub {
    my $thrNum = shift;
    # processing query
    while ( my $fileIn = $q->dequeue ) {
      my $fileOut = $fileIn;
      die "E: dirIn '$dirIn' not in fileIn '$fileIn'" if ( not $fileIn =~ m/$dirIn/ );
      $fileOut =~ s/$dirIn/$dirOut/;
      my ( $fname, $fdir, $fext ) = fileparse( $fileOut, qr/\.[^.]*/ );

      # Pfad anlegen
      unless ( -d $fdir ) {
        say encode( $decodingOut, decode( $decodingIn, "mkdir $fdir" ) );
        make_path( $fdir );
      }
      # say encode($decodingOut, decode($decodingIn,"$fileIn\n -> $fileOut"));
      say encode( $decodingOut, decode( $decodingIn, "$fileIn" ) );    # \n -> $fileOut"
      die "ERROR FileIn == FileOut!" if ( $fileIn eq $fileOut );

      # Convert using ImageMagic via shell
      my $s;
      if ( $fext =~ m/\.jpe?g$/i ) {
        $s = "magick convert \"$fileIn\" $convertPara \"$fileOut\"";
        # } elsif ($copyVideoFiles == 1 and ($fext =~ m/\.mp4$/i or $fext =~ m/\.mov$/i or $fext =~ m/\.mkv$/i or $fext =~ m/\.avi$/i) ) {
      } elsif ( $copyVideoFiles == 1 and ( grep { $fext eq '.' . $_ } @extVideos ) ) {
        say "W: No jpeg, but video -> copying instead of resizing";
        $s = "copy \"$fileIn\" \"$fileOut\"" if ( $os eq 'win' );
        $s = "cp \"$fileIn\" \"$fileOut\""   if ( $os eq 'lin' );
      } elsif ( $copyNonPictureFiles == 1 and not( grep { "$fname$fext" eq $_ } @filesIgnore ) ) {
        say "W: No jpeg, copying instead of resizing";
        $s = "copy \"$fileIn\" \"$fileOut\"" if ( $os eq 'win' );
        $s = "cp \"$fileIn\" \"$fileOut\""   if ( $os eq 'lin' );
      } else {
        say "Skipping non-image file $fileIn";
        next;
      }
      if ( $os eq 'win' ) {
        $s =~ s#/#\\#g;
      }
      # say encode($decodingOut, decode($decodingIn,$s));
      print `$s`;
    }    # while (my $fileIn = $q->dequeue)
    return;
  } ## end sub tsub

  # foreach my $fileIn (@listToExport) {

  # Filling the queue with the list
  $q->enqueue( $_ ) for ( @listToExport );
  for ( 1 .. $numThreads ) { $q->enqueue( undef ); }    # for stop condition
  # Fill the Threads Object
  for my $thrNum ( 1 .. $numThreads ) {
    push @Threads, threads->new( \&tsub, $thrNum );
  }

  # Wait for all threads to complete execution.
  foreach ( @Threads ) {
    print $_->join;                                     # wait for thread, returns return value
  }
  undef @Threads;
}    # for my $jahr


sub arrayMinus {
  # use @diff = arrayMinus(\@array1, \@array2)
  # returns A MINUS B
  my ( $refA, $refB ) = @_;
  my @A  = @{ $refA };
  my @B  = @{ $refB };
  my %hB = map { $_ => 1 } @B;
  # my @diff = grep {not $hB{$_}} @A; # einfach, langsam für große Listen
  my @diff;
  foreach my $item ( @A ) {
    if ( not exists( $hB{ $item } ) ) {
      push @diff, $item;
    } else {
      delete( $hB{ $item } );    # remove item from hash for speeding up checks
    }
  } ## end foreach my $item ( @A )
  return @diff;
} ## end sub arrayMinus


sub traverseDirGetFiles {
  my @queue = @_;
  my @listOfFiles;
  while ( @queue ) {
    my $thing = shift @queue;
    if ( -f $thing ) {
      push @listOfFiles, $thing;
    }
    next if not -d $thing;    # if thing = dir -> open it an query for traverseDirGetFiles
    opendir my $dh, $thing or die;
    while ( my $sub = readdir $dh ) {
      next if $sub eq '.' or $sub eq '..';
      push @queue, "$thing/$sub";
    }
    closedir $dh;
  } ## end while ( @queue )
  return @listOfFiles;
} ## end sub traverseDirGetFiles


sub traverseDirGetDirs {
  my @queue   = @_;
  my @initial = @_;
  my @listOfDirs;
  while ( @queue ) {
    my $thing = shift @queue;
    if ( -d $thing and not( grep { $thing eq $_ } @initial ) ) {    # is dir and is not one of the initial / starting dirs
      push @listOfDirs, $thing;
    }
    next if not -d $thing;                                          # if thing = dir -> open it an query for traverseDirGetFiles
    opendir my $dh, $thing or die;
    while ( my $sub = readdir $dh ) {
      next if $sub eq '.' or $sub eq '..';
      push @queue, "$thing/$sub";
    }
    closedir $dh;
  } ## end while ( @queue )
  return @listOfDirs;
} ## end sub traverseDirGetDirs
