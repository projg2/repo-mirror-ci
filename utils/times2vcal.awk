#!/usr/bin/awk -f
BEGIN {
	print "BEGIN:VCALENDAR";
	print "VERSION:1.0";
}

END {
	print "END:VCALENDAR";
}

{
	print "BEGIN:VEVENT";
	print "DTSTART:" gensub(/[-:]/, "", "g", $1);
	print "DTEND:" gensub(/[-:]/, "", "g", $2);
	print "SUMMARY:" FILENAME " (" FNR ")";
	print "CATEGORIES:" FILENAME;
	print "END:VEVENT";
}
