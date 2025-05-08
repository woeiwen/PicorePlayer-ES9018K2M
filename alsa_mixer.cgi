#!/bin/sh

# Version: 8.1.0 2021-08-30
# Modified: Added ES9018K2M DAC support

. pcp-functions
. pcp-soundcard-functions
. pcp-lms-functions

# Save copy of variable values so it is not overwritten with default values
ORIG_AUDIO="$AUDIO"
ORIG_CARD="$CARD"
ORIG_OUTPUT="$OUTPUT"
ORIG_ALSA_PARAMS="$ALSA_PARAMS"

pcp_html_head "Sound Mixer Controls" "PH"

pcp_picoreplayers_toolbar
pcp_controls
pcp_banner
pcp_navigation
[ $DEBUG -eq 0 ] && pcp_remove_query_string
pcp_httpd_query_string

unset REBOOT_REQUIRED

pcp_selected_soundcontrol
# ========== MODIFICATION: Enhanced card detection ==========

# First try exact match for ES9018K2M
ES9018_CARD=$(cat /proc/asound/cards | grep -i "es9018k2m" | head -1 | awk -F' ' '{print $1}')
if [ -n "$ES9018_CARD" ]; then
    CARD="$ES9018_CARD"
else
    # Fall back to original detection logic
    case "$CARD" in
        *USB*) CARD=$(cat /proc/asound/cards | grep USB | head -1 | awk -F' ' '{print$1}');;
    esac
fi

# Debug output
if [ $DEBUG -eq 1 ]; then
    echo "<!-- Card Detection Debug -->"
    echo "<!-- Original CARD: $ORIG_CARD -->"
    echo "<!-- Detected CARD: $CARD -->"
    echo "<!-- All Cards: -->"
    cat /proc/asound/cards
    echo "<!-- amixer controls for card $CARD: -->"
    amixer -c $CARD scontrols
fi

# Check for built-in soundcard
cat /proc/asound/cards | grep -q bcm2835
ACTUAL_ONBOARD_STATUS=$?
[ $ACTUAL_ONBOARD_STATUS -eq 0 ] && ONBOARD_SND="On" || ONBOARD_SND="Off"
[ "$ONBOARD_SND" = "On" ] && ONBOARD_SOUND_CHECK="checked" || ONBOARD_SOUND_CHECK=""

function urlencode() {
    echo "$1" | awk '
        BEGIN {
            for (i = 0; i <= 255; i++) {
                ord[sprintf("%c", i)] = i
            }
        }
        function escape(str, c, len, res) {
            len = length(str)
            res = ""
            for (i = 1; i <= len; i++) {
                c = substr(str, i, 1);
                if (c ~ /[0-9A-Za-z]/)
                    res = res c
                else
                    res = res "%" sprintf("%02X", ord[c])
            }
            return res
        }
        { print escape($0) }'
}

function urldecode() {
    echo "$1" | awk '{
        for (i = 0x20; i < 0x40; ++i) {
            repl = sprintf("%c", i);
            if ((repl == "&") || (repl == "\\"))
                repl = "\\" repl;
            gsub(sprintf("%%%02X", i), repl);
            gsub(sprintf("%%%02x", i), repl);
        }
        print
    }'
}

# ========== MODIFICATION: Enhanced control detection ==========
function read_mixer_controls() {
    local i=0
    local j=0
    local tmpfile=$(mktemp)

    amixer -c "$CARD" scontrols | sed 's/Simple mixer control //' | cut -d',' -f1 > $tmpfile

    while read line; do
        # Special handling for ES9018K2M DAC controls
        case "$line" in
            "I2S/SPDIF Input"|"FIR Filter"|"IIR Filter"|"I2S DPLL Bandwidth"|"DSD DPLL Bandwidth"|"Deemphasis Filter")
                eval CONTROL${i}="$(urlencode "$line")"
                eval CONTROLQS${i}="$(echo "$line" | tr -d '[:space:]-_'/\\ | tr -d "\'")"
                eval TYPE${i}="enum"
                eval JOINED${i}="False"
                i=$((i + 1))
                continue
                ;;
        esac

        eval CONTROL${i}="$(urlencode "$line")"
        #Remove spaces and characters from names for Querystring
        eval CONTROLQS${i}=\"$(echo "$line" | tr -d '[:space:]-_'/\\ | tr -d "\'")\"
        local CAP=$(amixer -c "$CARD" sget "$line" | grep Capabilities | sed 's/Capabilities: //')
        local CHAN=$(amixer -c "$CARD" sget "$line" | grep "Playback channels" | sed 's/Playback channels: //')
        case $CAP in
            *volume*)
                case $CAP in
                    *pvolume*) eval TYPE${i}="pvol";;
                    *volume*) eval TYPE${i}="vol";;
                esac
                case $CAP in
                    *volume-joined*) eval VOLJOINED${i}="True";;
                    *) eval VOLJOINED${i}="False";;
                esac
                case $CAP in
                    *switch*) eval MUTABLE${i}="True";;
                    *) eval MUTABLE${i}="False";;
                esac
                case $CAP in
                    *switch-joined*) eval MUTEJOINED${i}="True";;
                    *) eval MUTEJOINED${i}="False";;
                esac
                case $CHAN in
                    *Mono*) eval CHANNELS${i}="Mono";;
                    *) eval CHANNELS${i}="Left-Right";;
                esac
            ;;
            *enum*)
                eval TYPE${i}="enum"
                eval JOINED${i}="False"
            ;;
            *switch*)
                eval TYPE${i}="switch"
                case $CAP in
                    *joined*) eval JOINED${i}="Mono";;
                    *) eval JOINED${i}="False";;
                esac
                case $CHAN in
                    *Mono*) eval CHANNELS${i}="Mono";;
                    *) eval CHANNELS${i}="Left-Right";;
                esac
            ;;
        esac

        i=$((i + 1))
    done < $tmpfile
    rm -f $tmpfile

    NUM_CONTROLS=$i
}

# ========== MODIFICATION: Enhanced enum handling ==========
function read_mixer_values() {
    read_mixer_controls
    local i=0
    local j=0
    ID=200
    while [ $i -lt $NUM_CONTROLS ]; do
        local CNTRL="$(urldecode "$(eval echo \$CONTROL${i})")"
        local Type="$(eval echo \$TYPE${i})"
        eval CONTROLID${i}=$ID
        case $Type in
            *vol)
                # if we don't know what SSET is, make a guess that the first pvolume type is the master volume
                # **  Might be a bad Guess **
                [ "$SSET" = "" -a "$Type" = "pvol" ] && SSET="$(urldecode "$(eval echo \$CONTROL${i})")"
                # Type vol is shifted by 1 vs pvol
                [ "$Type" = "vol" ] && SHFT=1 || SHFT=0
                case "$(eval echo \$CHANNELS${i})" in
                    Mono)
                        eval VALUE${i}=$(amixer -c "$CARD" sget "$CNTRL" | grep "Mono:" | awk '{ print $(3-'$SHFT') }')
                        eval VALUEPERC${i}=$(amixer -c "$CARD" sget "$CNTRL" | grep "Mono:" | awk '{ print $(4-'$SHFT') }' | tr -d "[]%")
                        eval VALUEDB${i}=$(amixer -c "$CARD" sget "$CNTRL" | grep "Mono:" | awk '{ print $(5-'$SHFT') }' | tr -d "[]")
                    ;;
                    *)
                        eval VALUER${i}=$(amixer -c "$CARD" sget "$CNTRL" | grep "Right:" | awk '{ print $(4-'$SHFT') }')
                        eval VALUERPERC${i}=$(amixer -c "$CARD" sget "$CNTRL" | grep "Right:" | awk '{ print $(5-'$SHFT') }' | tr -d "[]%")
                        eval VALUERDB${i}=$(amixer -c "$CARD" sget "$CNTRL" | grep "Right:" | awk '{ print $(6-'$SHFT') }' | tr -d "[]")
                        eval VALUEL${i}=$(amixer -c "$CARD" sget "$CNTRL" | grep "Left:" | awk '{ print $(4-'$SHFT') }')
                        eval VALUELPERC${i}=$(amixer -c "$CARD" sget "$CNTRL" | grep "Left:" | awk '{ print $(5-'$SHFT') }' | tr -d "[]%")
                        eval VALUELDB${i}=$(amixer -c "$CARD" sget "$CNTRL" | grep "Left:" | awk '{ print $(6-'$SHFT') }' | tr -d "[]")
                    ;;
                esac
                case "$(eval echo \$MUTABLE${i})" in
                    True)
                        case "$(eval echo \$CHANNELS${i})" in
                            Mono) eval MUTE${i}=$(amixer -c "$CARD" sget "$CNTRL" | grep "Mono:" | awk '{ print $(6-'$SHFT') }' | tr -d "[]");;
                            *)    eval MUTER${i}=$(amixer -c "$CARD" sget "$CNTRL" | grep "Right:" | awk '{ print $(7-'$SHFT') }' | tr -d "[]")
                                  eval MUTEL${i}=$(amixer -c "$CARD" sget "$CNTRL" | grep "Left:" | awk '{ print $(7-'$SHFT') }' | tr -d "[]")
                            ;;
                        esac
                    ;;
                    False)
                        eval MUTE${i}=""
                    ;;
                esac
                eval LLIMIT${i}=$(amixer -c "$CARD" sget "$CNTRL" | grep Limits: | awk '{ print $(NF-2)}')
                eval HLIMIT${i}=$(amixer -c "$CARD" sget "$CNTRL" | grep Limits: | awk '{ print $(NF)}')
            ;;
            switch)
                case "$(eval echo \$CHANNELS${i})" in
                    Mono)
                        eval VALUE${i}=$(amixer -c "$CARD" sget "$CNTRL" | grep "Mono: Playback" | awk '{ print $3 }' | tr -d "[]")
                    ;;
                    *)
                        eval VALUER${i}=$(amixer -c "$CARD" sget "$CNTRL" | grep "Right: Playback" | awk '{ print $4 }' | tr -d "[]")
                        eval VALUEL${i}=$(amixer -c "$CARD" sget "$CNTRL" | grep "Left: Playback" | awk '{ print $4 }' | tr -d "[]")
                    ;;
                esac
            ;;
            enum)
                # Enhanced handling for enum controls
                tmpfile=$(mktemp)
                amixer -c "$CARD" sget "$CNTRL" | grep Items: | sed 's/  Items: //' | sed "s/' '/'pcp'/g" | awk -F'pcp' '{for (i=0; ++i <=NF;) print $i}' > $tmpfile
                j=0
                while read line; do
                    eval ENUM${i}_${j}="$(urlencode "$line")"
                    j=$((j+1))
                done < $tmpfile
                rm -f $tmpfile
                eval ENUM_QTY${i}=$j
                eval VALUE${i}="$(urlencode "$(amixer -c "$CARD" sget "$CNTRL" | grep Item0: |  sed 's/  Item0: //')")"
            ;;
        esac
        i=$((i + 1))
        ID=$((ID + 1))
    done
}

function set_mixer_values() {
    read_mixer_controls
    local i=0
    local j=0
    local length=${#CHANGED}
    local pos=0
    while [ $i -lt $NUM_CONTROLS ]; do
        pos=$(( $length - ($i + 1) ))
        if [ "${CHANGED:$pos:1}" = "1" ]; then
            [ $DEBUG -eq 1 ] && echo "${CHANGED} pos=$pos, length=$length, i=$i, setting this control"
            local CNTRL="$(urldecode "$(eval echo \$CONTROL${i})")"
            local CNTRLQS="$(eval echo \$CONTROLQS${i})"
            local Channels="$(eval echo \$CHANNELS${i})"
            local Mutable="$(eval echo \$MUTABLE${i})"
            case "$(eval echo \$TYPE${i})" in
                *vol)
                    #Set Volume Level
                    case $Channels in
                        Mono) amixer $QUIET -c "$CARD" -- sset "$CNTRL" $(eval echo \${${CNTRLQS}}) 2>&1;;
                        *)	amixer $QUIET -c "$CARD" -- sset "$CNTRL" frontleft $(eval echo \${${CNTRLQS}LEFT}) 2>&1
                            amixer $QUIET -c "$CARD" -- sset "$CNTRL" frontright $(eval echo \${${CNTRLQS}RIGHT}) 2>&1;;
                    esac
                    #Set Mute Switch
                    if [ "$Mutable" = "True" ]; then
                        case $Channels in
                            Mono)
                                val="$(eval echo \${${CNTRLQS}Mute})"
                                [ "$val" = "1" ] && val="mute" || val="unmute"
                                amixer $QUIET -c "$CARD" -- sset "$CNTRL" $val 2>&1
                            ;;
                            *)	#Set Left Mute, if mute controls are joined, this will set both.
                                val="$(eval echo \${${CNTRLQS}MuteL})"
                                [ "$val" = "1" ] && val="mute" || val="unmute"
                                amixer $QUIET -c "$CARD" -- sset "$CNTRL" frontleft,$val 2>&1
                                if [ "$(eval echo \${MUTEJOINED${i}})" = "False" ]; then
                                    #Set Right Mute, if mute controls are not joined
                                    val="$(eval echo \${${CNTRLQS}MuteR})"
                                    [ "$val" = "1" ] && val="mute" || val="unmute"
                                    amixer $QUIET -c "$CARD" -- sset "$CNTRL" frontright,$val 2>&1
                                fi
                            ;;
                        esac
                    fi
                ;;
                switch)
                    case $Channels in
                        Mono)
                            val="$(eval echo \${${CNTRLQS}})"
                            [ "$val" = "1" ] && val="on" || val="off"
                            amixer $QUIET -c "$CARD" -- sset "$CNTRL" $val 2>&1
                        ;;
                        *)
                            val="$(eval echo \${${CNTRLQS}L})"
                            [ "$val" = "1" ] && val="on" || val="off"
                            amixer $QUIET -c "$CARD" -- sset "$CNTRL" frontleft,$val 2>&1
                            val="$(eval echo \${${CNTRLQS}R})"
                            [ "$val" = "1" ] && val="on" || val="off"
                            amixer $QUIET -c "$CARD" -- sset "$CNTRL" frontright,$val 2>&1
                        ;;
                    esac
                ;;
                enum)
                    val="$(eval echo \${${CNTRLQS}} | tr -d "\'")"
                    amixer $QUIET -c "$CARD" -- sset "$CNTRL" "$val" 2>&1
                ;;
            esac
        fi
        i=$((i + 1))
    done
}

#========================================ACTIONS=========================================
[ $DEBUG -eq 0 ] && QUIET="-q" || QUIET=""
if [ "$ACTION" != "" ]; then
    pcp_table_top "Setting ALSA"
    echo '                <textarea class="inform" style="height:80px">'
fi
case "$ACTION" in
    Save)
        echo '[ INFO ] Setting ALSA mixer.'
        [ "${CHANGED}" != "0" ] && set_mixer_values
        AUDIO="$ORIG_AUDIO"
        OUTPUT="$ORIG_OUTPUT"
        ALSA_PARAMS="$ORIG_ALSA_PARAMS"
        echo '[ INFO ] Setting ALSAlevelout to Custom.'
        ALSAlevelout="Custom"
        pcp_save_to_config
        echo '[ INFO ] Saving ALSA State.'
        sudo alsactl store
        pcp_backup "text"
    ;;
    0dB)
        echo '[ INFO ] Setting volume to 0dB.'
        [ "$SSET" = "" ] && SSET=$VOLCTL
        sudo amixer $QUIET -c "$CARD" sset "$SSET" 0dB
        AUDIO="$ORIG_AUDIO"
        OUTPUT="$ORIG_OUTPUT"
        ALSA_PARAMS="$ORIG_ALSA_PARAMS"
        echo '[ INFO ] Setting ALSAlevelout to Custom.'
        ALSAlevelout="Custom"
        pcp_save_to_config
        echo '[ INFO ] Saving ALSA State.'
        sudo alsactl store
        pcp_backup "text"
    ;;
    4dB)
        echo '[ INFO ] Setting volume to 4dB.'
        sudo amixer $QUIET -c "$CARD" sset "$SSET" 4dB
        AUDIO="$ORIG_AUDIO"
        OUTPUT="$ORIG_OUTPUT"
        ALSA_PARAMS="$ORIG_ALSA_PARAMS"
        echo '[ INFO ] Setting ALSAlevelout to Custom.'
        ALSAlevelout="Custom"
        pcp_save_to_config
        echo '[ INFO ] Saving ALSA State.'
        sudo alsactl store
        pcp_backup "text"
    ;;
    Select)
        echo '[ INFO ] Setting soundcard driver parameters.'
        AUDIO="$ORIG_AUDIO"
        CARD="$ORIG_CARD"
        OUTPUT="$ORIG_OUTPUT"
        ALSA_PARAMS="$ORIG_ALSA_PARAMS"
        pcp_save_to_config
        pcp_read_chosen_audio
        pcp_backup "text"
        REBOOT_REQUIRED=TRUE
    ;;
    Onboard)
        # Check for changes in onboard status as we don't want to mount and umount if not needed
        SELECTED_BOARD="On"
        [ x"$ONBOARD" = x"" ] && SELECTED_BOARD="Off"
        if [ "$ONBOARD_SND" != "$SELECTED_BOARD" ]; then
            pcp_mount_bootpart "text" >/dev/null 2>&1
            if [ "$ONBOARD" = "On" ]; then
                echo '[ INFO ] Enabling RPi Built-in Audio.'
                pcp_re_enable_analog
            else
                echo '[ INFO ] Disabling RPi Built-in Audio.'
                pcp_disable_analog
                sudo rmmod snd_bcm2835
            fi
            # This page should not be changing ALSA_PARAMS.
            AUDIO="$ORIG_AUDIO"
            OUTPUT="$ORIG_OUTPUT"
            ALSA_PARAMS="$ORIG_ALSA_PARAMS"
            pcp_umount_bootpart "text"
            pcp_save_to_config
            pcp_backup "text"
            REBOOT_REQUIRED=TRUE
        fi
    ;;
    Reset)
        echo '[ INFO ] Removing ALSA saved states.'
        rm -f /var/lib/alsa/asound.state
        touch /var/lib/alsa/asound.state
        echo '[ INFO ] Setting ALSAlevelout to Default.'
        AUDIO="$ORIG_AUDIO"
        OUTPUT="$ORIG_OUTPUT"
        ALSA_PARAMS="$ORIG_ALSA_PARAMS"
        ALSAlevelout="Default"
        pcp_save_to_config
        pcp_backup "text"
    ;;
esac
if [ "$ACTION" != "" ]; then
    echo '                </textarea>'
    pcp_table_end
    [ $REBOOT_REQUIRED ] && pcp_reboot_required
fi
#----------------------------------------------------------------------------------------

#========================================DEBUG===========================================
if [ $DEBUG -eq 1 ]; then
    echo '<!-- Start of debug info -->'
    pcp_debug_variables "html" ACTION AUDIO ORIG_OUTPUT OUTPUT CARD SSET DSP_CONTROL \
        DTOVERLAY GENERIC_CARD \
        PARAMS1 PARAMS2 PARAMS3 PARAMS4 PARAMS5 \
        ALSA_PARAMS\
        NUM_CONTROLS
    echo '<!-- End of debug info -->'
fi

row_padding() {
    echo '            <tr class="padding '$ROWSHADE'">'
    echo '              <td colspan="4">'
    echo '              </td>'
    echo '            </tr>'
}

pcp_alsa_show_controls() {
    i=0
    if [ $NUM_CONTROLS -eq 0 ]; then
        echo '            <tr class="'$ROWSHADE'">'
        echo '              <td colspan="5">'
        echo '                <p>&nbsp;&nbsp;Your card does not have any mixer controls.</p>'
        echo '              </td>'
        echo '            </tr>'
    fi
    while [ $i -lt $NUM_CONTROLS ]; do
        local CNTRL="$(urldecode "$(eval echo \$CONTROL${i})")"
        local CNTRLQS="$(eval echo \$CONTROLQS${i})"
        local Type=$(eval echo \$TYPE${i})
        if [ "$Type" = "vol" -o "$Type" = "pvol" ]; then
            local Step=$(echo "$(eval echo \$HLIMIT${i}) $(eval echo \$LLIMIT${i})" | awk '{print ($1-$2)/200}')
            Step=$(echo $Step | awk '{if ($1 < 1) {print 1} else {print $1} }')
            case $(eval echo \$CHANNELS${i}) in
                Mono)
                    echo '            <tr class="'$ROWSHADE'">'
                    echo '              <td class="'$COL1'">'
                    echo '                <p><b>'$CNTRL' Volume Level</b></p>'
                    echo '              </td>'
                    echo '              <td>'
                    echo '                <p style="height:30px">'
                    #The hidden control is the actual mixer control. Will allow the slider steps not to update the control...when only setting mute.
                    echo '                  <input type="hidden" name="'$CNTRLQS'" value="'$(eval echo \$VALUE${i})'">'
                    echo '                  <input class="large36"'
                    echo '                         id="'$CNTRLQS'INId"'
                    echo '                         type="range"'
                    echo '                         name="'$CNTRLQS'range"'
                    echo '                         value="'$(eval echo \$VALUE${i})'"'
                    echo '                         min="'$(eval echo \$LLIMIT${i})'"'
                    echo '                         max="'$(eval echo \$HLIMIT${i})'"'
                    echo '                         step="'$Step'"'
                    echo '                         oninput="'$CNTRLQS'OUTId.value = '$CNTRLQS'INId.value; '$CNTRLQS'.value = '$CNTRLQS'INId.value;"'
                    echo '                         onclick="setcontrols('$i');">'
                    echo '                </p>'
                    echo '              </td>'
                    echo '              <td class="column75">'
                    echo '                <output name="'$CNTRLQS'OUT" id="'$CNTRLQS'OUTId">'$(eval echo \$VALUE${i})'<br>'$(eval echo \$VALUEDB${i})'</output>'
                    echo '              </td>'
                    if [ "$(eval echo \$MUTABLE${i})" = "True" ]; then
                        case $(eval echo \$MUTE${i}) in
                            off) checked="checked";;
                            on) checked="";;
                        esac
                        echo '              <td class="'$COL3'">'
                        echo '                <input id="cb'${i}'" type="checkbox" name="'$CNTRLQS'Mute" value="1" '"${checked}"' onclick="setcontrols('$i');">'
                        echo '                <label for="cb'${i}'">&#8239;</label>'
                        echo '              </td>'
                        echo '              <td class="'$COL4'">'
                        echo '                <p>Mute</p>'
                        echo '              </td>'
                    else
                        echo '              <td colspan="2"></td>'
                    fi
                    echo '            </tr>'
                ;;
                *)	#Left Channel
                    echo '            <tr class="'$ROWSHADE'">'
                    echo '              <td class="'$COL1'">'
                    echo '                <p><b>'$CNTRL' Volume Level Left</b></p>'
                    echo '              </td>'
                    echo '              <td>'
                    echo '                <p style="height:30px">'
                    #The hidden control is the actual mixer control. Will allow the slider steps not to update the control...when only setting mute.
                    echo '                  <input type="hidden" name="'$CNTRLQS'LEFT" value="'$(eval echo \$VALUEL${i})'">'
                    echo '                  <input class="large36"'
                    echo '                         id="'$CNTRLQS'LeftINId"'
                    echo '                         type="range"'
                    echo '                         name="'$CNTRLQS'Lrange"'
                    echo '                         value="'$(eval echo \$VALUEL${i})'"'
                    echo '                         min="'$(eval echo \$LLIMIT${i})'"'
                    echo '                         max="'$(eval echo \$HLIMIT${i})'"'
                    echo '                         step="'$Step'"'
                    echo '                         oninput="'$CNTRLQS'LeftOUTId.value = '$CNTRLQS'LeftINId.value; '$CNTRLQS'LEFT.value = '$CNTRLQS'LeftINId.value;"'
                    echo '                         onclick="setcontrols('$i');">'
                    echo '                </p>'
                    echo '              </td>'
                    echo '              <td class="column75">'
                    echo '                <output name="'$CNTRLQS'LeftOUT" id="'$CNTRLQS'LeftOUTId">'$(eval echo \$VALUEL${i})'<br>'$(eval echo \$VALUELDB${i})'</output>'
                    echo '              </td>'
                    if [ "$(eval echo \$MUTABLE${i})" = "True" ]; then
                        case $(eval echo \$MUTEL${i}) in
                            off) checked="checked";;
                            on) checked="";;
                        esac
                        echo '              <td class="'$COL3'">'
                        echo '                <input id="cb'${i}L'" type="checkbox" name="'$CNTRLQS'MuteL" value="1" '"${checked}"' onclick="setcontrols('$i');">'
                        echo '                <label for="cb'${i}L'">&#8239;</label>'
                        echo '              </td>'
                        echo '              <td class="'$COL4'">'
                        echo '                <p>Mute</p>'
                        echo '              </td>'
                    else
                        echo '              <td colspan="2"></td>'
                    fi
                    echo '            </tr>'
                    # Right Channel
                    echo '            <tr class="'$ROWSHADE'">'
                    echo '              <td class="'$COL1'">'
                    echo '                <p><b>'$CNTRL' Volume Level Right</b></p>'
                    echo '              </td>'
                    echo '              <td>'
                    echo '                <p style="height:30px">'
                    #The hidden control is the actual mixer control. Will allow the slider steps not to update the control...when only setting mute.
                    echo '                  <input type="hidden" name="'$CNTRLQS'RIGHT" value="'$(eval echo \$VALUER${i})'">'
                    echo '                  <input class="large36"'
                    echo '                         id="'$CNTRLQS'RightINId"'
                    echo '                         type="range"'
                    echo '                         name="'$CNTRLQS'Rrange"'
                    echo '                         value="'$(eval echo \$VALUER${i})'"'
                    echo '                         min="'$(eval echo \$LLIMIT${i})'"'
                    echo '                         max="'$(eval echo \$HLIMIT${i})'"'
                    echo '                         step="'$Step'"'
                    echo '                         oninput="'$CNTRLQS'RightOUTId.value = '$CNTRLQS'RightINId.value; '$CNTRLQS'RIGHT.value = '$CNTRLQS'RightINId.value;"'
                    echo '                         onclick="setcontrols('$i');">'
                    echo '                </p>'
                    echo '              </td>'
                    echo '              <td class="column75">'
                    echo '                <output name="'$CNTRLQS'RightOUT" id="'$CNTRLQS'RightOUTId">'$(eval echo \$VALUER${i})'<br>'$(eval echo \$VALUERDB${i})'</output>'
                    echo '              </td>'
                    if [ "$(eval echo \${MUTEJOINED${i}})" = "False" ]; then
                        if [ "$(eval echo \$MUTABLE${i})" = "True" ]; then
                            case $(eval echo \$MUTER${i}) in
                                off) checked="checked";;
                                on) checked="";;
                            esac
                            echo '              <td class="'$COL3'">'
                            echo '                <input id="cb'${i}R'" type="checkbox" name="'$CNTRLQS'MuteR" value="1" '"${checked}"' onclick="setcontrols('$i');">'
                            echo '                <label for="cb'${i}R'">&#8239;</label>'
                            echo '              </td>'
                            echo '              <td class="'$COL4'">'
                            echo '                <p>Mute</p>'
                            echo '              </td>'
                        else
                            echo '              <td colspan="2"></td>'
                        fi
                        echo '            </tr>'
                    else
                        echo '              <td colspan="3">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Mute controls joined.</td>'

                    fi
                ;;
            esac
            pcp_toggle_row_shade
        fi
        if [ "$Type" = "switch" ]; then
            case $(eval echo \$CHANNELS${i}) in
                Mono)
                    case $(eval echo \$VALUE${i}) in
                        on) checked="checked";;
                        off) checked="";;
                    esac
                    echo '            <tr class="'$ROWSHADE'">'
                    echo '              <td class="'$COL1'">'
                    echo '                <p><b>'$CNTRL'</b></p>'
                    echo '              </td>'
                    echo '              <td class="'$COL2'" colspan="4">'
                    echo '                <input id="cb'${i}'" type="checkbox" name="'$CNTRLQS'" value="1" '"${checked}"' onclick="setcontrols('$i');">'
                    echo '                <label for="cb'${i}'" style="margin-left:40px;">&#8239;</label>'
                    echo '              </td>'
                    echo '            </tr>'
                ;;
                *)	#Left
                    case $(eval echo \$VALUEL${i}) in
                        on) checked="checked";;
                        off) checked="";;
                    esac
                    echo '            <tr class="'$ROWSHADE'">'
                    echo '              <td class="'$COL1'">'
                    echo '                <p><b>'$CNTRL' Left</b></p>'
                    echo '              </td>'
                    echo '              <td class="'$COL2'" colspan="4">'
                    echo '                <input id="cb'${i}L'" type="checkbox" name="'$CNTRLQS'L" value="1" '"${checked}"' onclick="setcontrols('$i');">'
                    echo '                <label for="cb'${i}L'" style="margin-left:40px;">&#8239;</label>'
                    echo '              </td>'
                    echo '            </tr>'
                    #Right
                    case $(eval echo \$VALUER${i}) in
                        on) checked="checked";;
                        off) checked="";;
                    esac
                    echo '            <tr class="'$ROWSHADE'">'
                    echo '              <td class="'$COL1'">'
                    echo '                <p><b>'$CNTRL' Right</b></p>'
                    echo '              </td>'
                    echo '              <td class="'$COL2'" colspan="4">'
                    echo '                <input id="cb'${i}'" type="checkbox" name="'$CNTRLQS'R" value="1" '"${checked}"' onclick="setcontrols('$i');">'
                    echo '                <label for="cb'${i}'" style="margin-left:40px;">&#8239;</label>'
                    echo '              </td>'
                    echo '            </tr>'
                ;;
            esac
        fi

        if [ "$Type" = "enum" ]; then
            local NUM=$(eval echo \$ENUM_QTY${i})
            local CurVALUE="$(urldecode "$(eval echo \$VALUE${i})")"
            local val=""
            j=0
            echo '            <tr class="'$ROWSHADE'">'
            echo '              <td class="'$COL1'">'
            echo '                <p><b>'$CNTRL'</b></p>'
            echo '              </td>'
            echo '              <td class="column300 right" colspan="4">'
            echo '                <select class="large20" id="'$CNTRLQS'Id" name="'$CNTRLQS'" onclick="setcontrols('$i');">'
            while [ $j -lt $NUM ]; do
                val="$(urldecode "$(eval echo \$ENUM${i}_${j})")"
                [ "$CurVALUE" = "$val" ] && sel="selected" || sel=""
                echo '                  <option value="'$val'" '$sel'>'$(echo $val|tr -d "\'")'</option>'
                j=$((j+1))
            done
            echo '                </select>'
            echo '              </td>'
            echo '            </tr>'
        fi
        i=$((i + 1))
    done
    echo '<script>'
    echo '  bintable=[1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576, 2097152, 4194304, 8388608, 16777216, 33554432, 67108864, 134217728, 268435456, 536870912 ];'
    echo '  cntrl=1073741824;'
    echo '  function setcontrols( c) {'
    echo '    if ( c <= 30 ) {'
    echo '      cntrl = cntrl | bintable[c];'
    echo '      document.getElementById("MixersToSet").value = cntrl.toString(2);'
    echo '    }'
    echo '  }'
    echo '</script>'
}

pcp_volume_filter_buttons() {
    pcp_incr_id
    echo '            <tr class="'$ROWSHADE'">'
    echo '              <td class="column120 center">'
    echo '                <input type="hidden" id="MixersToSet" name="CHANGED" value="0">'
    echo '                <input type="submit" name="ACTION" value="Save">'
    echo '              </td>'
    if [ "$SSET" != "" ]; then
        echo '              <td class="column120 center">'
        echo '                <input type="hidden" name="VOLCTL" value="'$SSET'">'
        echo '                <input type="submit" name="ACTION" value="0dB">'
        echo '              </td>'
    else
        echo '              <td></td>'
    fi
    if [ "$CARD" = "Headphones" -o "$CARD" = "b1" -o "$CARD" = "b2" ]; then
        echo '              <td class="column120 center">'
        echo '                <input type="submit" name="ACTION" value="4dB">'
        echo '              </td>'
    else
        echo '              <td></td>'
    fi
    if [ $NUM_CONTROLS -gt 30 ]; then
        msg="This page can only set the first 30 controls"
    else
        msg=""
    fi
    echo '              <td colspan="2">'
    echo '                <p>'
    echo '                  <a id="'$ID'a" class="moreless" href=# onclick="return more('\'''$ID''\'')">&nbsp;'$msg'&nbsp;&nbsp;more></a>'
    echo '                </p>'
    echo '                <div id="'$ID'" class="less">'
    echo '                  <p>Use above control(s) to set the ALSA mixer, then</p>'
    echo '                  <ul>'
    echo '                    <li><b>Save</b> - The output setting(s) are saved up to make them available after a reboot.</li>'
    if [ "$SSET" != "" ]; then
        echo '                    <li><b>0dB</b> - Set output level to 0dB.</li>'
    fi
    if [ "$CARD" = "Headphones" -o "$CARD" = "b1" -o "$CARD" = "b2" ]; then
        echo '                    <li><b>4dB</b> - Set output level to 4dB (100%).</li>'
    fi
    echo '                  </ul>'
    echo '                </div>'
}

pcp_reset_alsactl() {
    pcp_toggle_row_shade
    pcp_incr_id
    pcp_table_top "Reset ALSA Configuration" "class=\"column120 center\""
    echo '                <input type="submit" name="ACTION" value="Reset">'
    echo '              </td>'
    echo '              <td>'
    echo '                <p>Reset saved ALSA settings&nbsp;&nbsp;'
    echo '                  <a id="'$ID'a" class="moreless" href=# onclick="return more('\'''$ID''\'')">more></a>'
    echo '                </p>'
    echo '                <div id="'$ID'" class="less">'
    echo '                  <p>After reset, you will need to resave mixer settings.</p>'
    echo '                </div>'
    pcp_table_end
}

#========================================================================================
# Parameter options
# - Only show these options if Parameters for dtoverlay are an option for current
#   sound card.
#----------------------------------------------------------------------------------------
pcp_soundcard_parameter_options() {
    . $PCPCFG
    if [ "${PARAMS1}${PARAMS2}${PARAMS3}${PARAMS4}${PARAMS5}" != "" ]; then
        pcp_table_end
        pcp_incr_id
        pcp_start_row_shade
        pcp_table_top "Dtoverlay parameter options"
        I=1
        while [ $I -le 5 ]; do
            [ "$(eval echo "\${SPARAMS${I}}")" != "" ] && eval PARAMS${I}_CHECK="checked"
            [ "$(eval echo "\${PARAMS${I}}")" != "" ] && echo '                <input id="PARAMS'$I'" type="checkbox" name="PARAM'$I'" value='$(eval echo \${PARAMS${I}})' '$(eval echo \${PARAMS${I}_CHECK})'><label for="PARAMS'$I'"> '$(eval echo \${PARAMS${I}})'</label><br style="line-height:30px;">'
            I=$((I+1))
        done
        #--------------------------------------------------------------------------------
        pcp_table_middle
        echo '                <button type="submit" name="ACTION" value="Select">Save</button>'
    fi

    if [ x"$TEXT1" != x"" ]; then
        pcp_table_middle
        pcp_incr_id
        echo '                <p><b>Parameters and notes for your DAC&nbsp;&nbsp;</b>'
        echo '                  <a id="'$ID'a" class="moreless" href=# onclick="return more('\'''$ID''\'')">more></a>'
        echo '                </p>'
        echo '                <div id="'$ID'" class="less">'
        echo '                  <p>Select the parameters you want to add to dtoverlay for your DAC. <b>Then a reboot is needed.</b></p>'
        echo '                  <ul>'
        I=1
        while true; do
            eval CHK="\${TEXT${I}}"
            if [ x"$CHK" != x"" ]; then
                echo -n '                    <li>'
                eval echo -n "\${TEXT${I}}"
                echo '</li>'
                I=$((I+1))
            else
                break
            fi
        done
        echo '                  </ul>'
        echo '                </div>'
    fi
}

pcp_show_text() {
    echo '                  <p>Notes for your DAC.</p>'
    echo '                  <ul>'
    I=1
    while true; do
        eval CHK="\${TEXT${I}}"
        if [ x"$CHK" != x"" ]; then
            echo -n '                    <li>'
            eval echo -n "\${TEXT${I}}"
            echo '</li>'
            I=$((I+1))
        else
            break
        fi
    done
    echo '                  </ul>'
}

pcp_save_button() {
    pcp_incr_id
    echo '            <tr class="'$ROWSHADE'">'
    echo '              <td class="column120 center">'
    echo '                <input type="submit" name="ACTION" value="Save">'
    echo '              </td>'
    echo '              <td>'
    echo '                <p>Save ALSA mixer settings to make them available after a reboot.</p>'
    echo '              </td>'
    echo '            </tr>'
}

#========================================================================================
# Enable/disable built-in analoq sound
#----------------------------------------------------------------------------------------
pcp_disable_enable_builtin_sound() {
    if [ "$GENERIC_CARD" != "ONBOARD" ]; then
        pcp_start_row_shade
        pcp_incr_id
        pcp_table_top "Raspberry Pi Built-in Audio" "colspan=\"2\""
        echo '                <p><b>Enable/disable built-in audio (after a reboot)</b></p>'
        pcp_table_middle "class=\"column120 center\""
        echo '                <p><input id="cbob" type="checkbox" name="ONBOARD" value="On" '"$ONBOARD_SOUND_CHECK"'>'
        echo '                  <label for="cbob">&#8239;</label>'
        echo '              </td>'
        echo '              <td>'
        echo '                <p>When checked - built-in audio is enabled&nbsp;&nbsp;'
        echo '                  <a id="'$ID'a" class="moreless" href=# onclick="return more('\'''$ID''\'')">more></a>'
        echo '                </p>'
        echo '                <div id="'$ID'" class="less">'
        echo '                  <p>Enable (with check) or disable (no check) the built-in audio. <b>Then a reboot is needed.</b></p>'
        echo '                </div>'
        pcp_table_middle "class=\"column120 center\" colspan=\"2\""
        echo '                <button type="submit" name="ACTION" value="Onboard">Save</button>'
        pcp_table_end
    fi
}

read_mixer_values

if [ $DEBUG -eq 1 ]; then
    echo '<!-- Start of debug info -->'
    pcp_debug_variables "html" NUM_CONTROLS CHANNELS0
    echo '<!-- End of debug info -->'
fi

#========================================================================================
# Below is the blocks that builds the table
#----------------------------------------------------------------------------------------
COL1="column150 center"
COL2="column300 left"
COL3="column75 right"
COL4="column50"

echo '<form name="card_controls" action="'$0'" method="get">'
pcp_start_row_shade
pcp_incr_id
pcp_table_top "ALSA Mixer Adjustment for: $LISTNAME" "colspan=\"5\""
# Just close the automatic table row from table top, since there is no set order of the mixer controls.
echo '              </td>'
echo '            </tr>'
pcp_alsa_show_controls
[ $NUM_CONTROLS -gt 0 ] && pcp_volume_filter_buttons

pcp_soundcard_parameter_options

pcp_table_end

pcp_reset_alsactl

pcp_disable_enable_builtin_sound
echo '</form>'
#----------------------------------------------------------------------------------------

pcp_footer
pcp_copyright

echo '</body>'
echo '</html>'
