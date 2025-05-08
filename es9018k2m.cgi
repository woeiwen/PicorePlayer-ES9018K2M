#!/bin/sh

# Version: 6.0.0 2019-07-18
# Modified for ES9018K2M DAC

. pcp-functions
. pcp-soundcard-functions


pcp_httpd_query_string

pcp_html_head "ES9018K2M DAC CONTROL" "DAC"

pcp_picoreplayers_toolbar
pcp_banner
pcp_navigation

card_id=`aplay -l | grep "es9018k2m" | sed 's/card \([0-9+]\).*$/\1/'`
if test -z "$card_id"
then
	echo '<p class="error">[ ERROR ] ES9018K2M DAC not detected...</p>'
	exit 0
else 

current_iir=`amixer sget -c $card_id 'IIR Filter Select' | grep Item0: | sed "s/^.*\?'\(.*\)'/\1/g"`
current_fir=`amixer sget -c $card_id 'FIR Filter Select' | grep Item0: | sed "s/^.*\?'\(.*\)'/\1/g"`
current_dpll=`amixer sget -c $card_id 'I2S DPLL Bandwidth' | grep Item0: | sed "s/^.*\?'\(.*\)'/\1/g"`
current_dsd_dpll=`amixer sget -c $card_id 'DSD DPLL Bandwidth' | grep Item0: | sed "s/^.*\?'\(.*\)'/\1/g"`
current_deemphasis=`amixer sget -c $card_id 'Deemphasis Filter' | grep Item0: | sed "s/^.*\?'\(.*\)'/\1/g"`

case "$SUBMIT" in
		"");;
        toggle_iir)
			filters=`amixer sget -c $card_id 'IIR Filter Select' | grep Items | sed "s/^.*Items:[^']*'\(.*\)'/\1/; s/' '/\n/g"` 
			length=`echo "$filters" | wc -l`
			current_index=`echo "$filters" | grep -wxn "$current_iir" | sed 's/:.*$//'`
			next_index=`echo "($current_index) % ($length) +1" | bc`
			next_filter=`echo "$filters" | sed "$next_index""q;d"`
			amixer sset -c $card_id 'IIR Filter Select' "$next_filter"  > /dev/null
			current_iir=$next_filter
			echo "<p class='ok'>[ CYCLE IIR FILTER ] ${current_iir} </p>"
        ;;
		toggle_fir)
			filters=`amixer sget -c $card_id 'FIR Filter Select' | grep Items | sed "s/^.*Items:[^']*'\(.*\)'/\1/; s/' '/\n/g"` 
			length=`echo "$filters" | wc -l`
			current_index=`echo "$filters" | grep -wxn "$current_fir" | sed 's/:.*$//'`
			next_index=`echo "($current_index) % ($length) +1" | bc`
			next_filter=`echo "$filters" | sed "$next_index""q;d"`
			amixer sset -c $card_id 'FIR Filter Select' "$next_filter"  > /dev/null
			current_fir=$next_filter
			echo "<p class='ok'>[ CYCLE FIR FILTER ] ${current_fir} </p>"
		;;
		toggle_dpll)
			values=`amixer sget -c $card_id 'I2S DPLL Bandwidth' | grep Items | sed "s/^.*Items:[^']*'\(.*\)'/\1/; s/' '/\n/g"` 
			length=`echo "$values" | wc -l`
			current_index=`echo "$values" | grep -wxn "$current_dpll" | sed 's/:.*$//'`
			next_index=`echo "($current_index) % ($length) +1" | bc`
			next_value=`echo "$values" | sed "$next_index""q;d"`
			amixer sset -c $card_id 'I2S DPLL Bandwidth' "$next_value"  > /dev/null
			current_dpll=$next_value
			echo "<p class='ok'>[ CYCLE I2S DPLL ] ${current_dpll} </p>"
		;;
		toggle_dsd_dpll)
			values=`amixer sget -c $card_id 'DSD DPLL Bandwidth' | grep Items | sed "s/^.*Items:[^']*'\(.*\)'/\1/; s/' '/\n/g"` 
			length=`echo "$values" | wc -l`
			current_index=`echo "$values" | grep -wxn "$current_dsd_dpll" | sed 's/:.*$//'`
			next_index=`echo "($current_index) % ($length) +1" | bc`
			next_value=`echo "$values" | sed "$next_index""q;d"`
			amixer sset -c $card_id 'DSD DPLL Bandwidth' "$next_value"  > /dev/null
			current_dsd_dpll=$next_value
			echo "<p class='ok'>[ CYCLE DSD DPLL ] ${current_dsd_dpll} </p>"
		;;
		toggle_deemphasis)
			values=`amixer sget -c $card_id 'Deemphasis Filter' | grep Items | sed "s/^.*Items:[^']*'\(.*\)'/\1/; s/' '/\n/g"` 
			length=`echo "$values" | wc -l`
			current_index=`echo "$values" | grep -wxn "$current_deemphasis" | sed 's/:.*$//'`
			next_index=`echo "($current_index) % ($length) +1" | bc`
			next_value=`echo "$values" | sed "$next_index""q;d"`
			amixer sset -c $card_id 'Deemphasis Filter' "$next_value"  > /dev/null
			current_deemphasis=$next_value
			echo "<p class='ok'>[ CYCLE DEEMPHASIS ] ${current_deemphasis} </p>"
		;;
        *)
                echo '<p class="error">[ ERROR ] Invalid case argument.</p>'
        ;;
esac


echo ''
echo '<table class="bggrey">'
echo '  <tbody>'
echo '    <tr>'
echo '      <td>'
echo '        <div class="row">'
echo '          <fieldset>'
echo '            <legend>ES9018K2M DAC Control</legend>'
echo '            <table class="bggrey percent100">'
echo '              <tbody>'

echo '                <tr class="even">'
echo '                  <td class="column150 center">'
echo '                    <form name="Update" action="es9018k2m.cgi" method="get">'
echo '                      <button type="submit" name="SUBMIT" value="toggle_fir">Toggle FIR</button>'
echo '                    </form>'
echo '                  </td>'
echo '                  <td>'
echo '                    <p>Current FIR Filter : '
echo "$current_fir"
echo " 						<a id='fir_morea' class='moreless' href='#' onclick=\"return more('fir_more')\">more&gt;</a>"
echo '                    </p>'
echo '                    <div id="fir_more" class="less">'
echo '                      <p>Cycles between FIR filters: Slow Roll Off, Fast Roll Off, Minimum Phase, Bypass Oversampling</p>'
echo '                    </div>'
echo '                  </td>'
echo '                </tr>'

echo '                <tr class="odd">'
echo '                  <td class="column150 center">'
echo '                    <form name="Update" action="es9018k2m.cgi" method="get">'
echo '                      <button type="submit" name="SUBMIT" value="toggle_iir">Toggle IIR</button>'
echo '                    </form>'
echo '                  </td>'
echo '                  <td>'
echo '                    <p>Current IIR Filter : '
echo "$current_iir"
echo " 						<a id='iir_morea' class='moreless' href='#' onclick=\"return more('iir_more')\">more&gt;</a>"
echo '                    </p>'
echo '                    <div id="iir_more" class="less">'
echo '                      <p>Cycles between IIR filters: 47K (PCM), 50K (DSD), 60K (DSD), 70K (DSD), Bypass</p>'
echo '                    </div>'
echo '                  </td>'
echo '                </tr>'

echo '                <tr class="even">'
echo '                  <td class="column150 center">'
echo '                    <form name="Update" action="es9018k2m.cgi" method="get">'
echo '                      <button type="submit" name="SUBMIT" value="toggle_dpll">Toggle I2S DPLL</button>'
echo '                    </form>'
echo '                  </td>'
echo '                  <td>'
echo '                    <p>Current I2S DPLL Bandwidth : '
echo "$current_dpll"
echo " 						<a id='dpll_morea' class='moreless' href='#' onclick=\"return more('dpll_more')\">more&gt;</a>"
echo '                    </p>'
echo '                    <div id="dpll_more" class="less">'
echo '                      <p>Cycles between I2S DPLL bandwidth values: 00 to 15</p>'
echo '                    </div>'
echo '                  </td>'
echo '                </tr>'

echo '                <tr class="odd">'
echo '                  <td class="column150 center">'
echo '                    <form name="Update" action="es9018k2m.cgi" method="get">'
echo '                      <button type="submit" name="SUBMIT" value="toggle_dsd_dpll">Toggle DSD DPLL</button>'
echo '                    </form>'
echo '                  </td>'
echo '                  <td>'
echo '                    <p>Current DSD DPLL Bandwidth : '
echo "$current_dsd_dpll"
echo " 						<a id='dsd_dpll_morea' class='moreless' href='#' onclick=\"return more('dsd_dpll_more')\">more&gt;</a>"
echo '                    </p>'
echo '                    <div id="dsd_dpll_more" class="less">'
echo '                      <p>Cycles between DSD DPLL bandwidth values: 09 to 15</p>'
echo '                    </div>'
echo '                  </td>'
echo '                </tr>'

echo '                <tr class="even">'
echo '                  <td class="column150 center">'
echo '                    <form name="Update" action="es9018k2m.cgi" method="get">'
echo '                      <button type="submit" name="SUBMIT" value="toggle_deemphasis">Toggle Deemphasis</button>'
echo '                    </form>'
echo '                  </td>'
echo '                  <td>'
echo '                    <p>Current Deemphasis Filter : '
echo "$current_deemphasis"
echo " 						<a id='deemphasis_morea' class='moreless' href='#' onclick=\"return more('deemphasis_more')\">more&gt;</a>"
echo '                    </p>'
echo '                    <div id="deemphasis_more" class="less">'
echo '                      <p>Cycles between Deemphasis Filter values: Off, 32K, 44.1K, 48K</p>'
echo '                    </div>'
echo '                  </td>'
echo '                </tr>'

echo '			  </tbody>'
echo '            </table>'
echo '          </fieldset>'
echo '        </div>'
echo '      </td>'
echo '    </tr>'
echo '  </tbody>'
echo '</table>'
echo ''

fi

pcp_html_end
