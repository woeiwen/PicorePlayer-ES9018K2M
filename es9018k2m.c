/*
 * Driver for the ESS SABRE9018Q2C
 *
 * Author: Satoru Kawase, Takahito Nishiara
 *      Copyright 2016
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * version 2 as published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 */

 #include <linux/init.h>
 #include <linux/module.h>
 #include <linux/regmap.h>
 #include <linux/i2c.h>
 #include <sound/soc.h>
 #include <sound/pcm_params.h>
 #include <sound/tlv.h>
 #include <linux/bitops.h>
 #include "es9018k2m.h"
 
 /* SABRE9018Q2C Codec Private Data */
 struct es9018k2m_priv {
     struct regmap *regmap;
     unsigned int fmt;
     struct snd_soc_component *component;
 };
 
 static uint8_t SABRE9018Q2C_VOLUME1;
 static uint8_t SABRE9018Q2C_VOLUME2;
 static bool SABRE9018Q2C_isMuted;


 /* SABRE9018Q2C Default Register Value */
 static const struct reg_default es9018k2m_reg_defaults[] = {
     { 0, 0x00 },
     { 1, 0x8c },
     { 4, 0x00 },
     { 5, 0x68 },
     { 6, 0x42 },
     { 7, 0x80 },
     { 8, 0x10 },
     { 9, 0x00 },
     { 10,0x00 },
     { 11,0x02 },
     { 12,0x5a },
     { 13,0x40 },
     { 14,0x8a },
     { 15,0x80 },
     { 16,0x80 },
     { 17,0xff },
     { 18,0xff },
     { 19,0xff },
     { 20,0x7f },
     { 21,0x00 },
     { 26,0x00 },
     { 27,0x00 },
     { 28,0x00 },
     { 29,0x00 },
     { 30,0x00 },

 };
 
 static bool es9018k2m_writeable(struct device *dev, unsigned int reg)
 {
    if (reg > ES9018K2M_CACHEREGNUM)
        return false;
    return (reg != 0x02 && reg != 0x03);
}
 
 static bool es9018k2m_readable(struct device *dev, unsigned int reg)
 {
     if (reg <= ES9018K2M_CACHEREGNUM && reg != 2 && reg != 3)
         return true;
     else if (65 <= reg && reg <= 69)
         return true;
     else if (70 <= reg && reg <= 93)
         return true;
     else
         return false;
 }
 
 static bool es9018k2m_volatile(struct device *dev, unsigned int reg)
 {
     return false;
 }
 
 static int es9018k2m_mute(struct snd_soc_dai *dai, int mute, int direction)
 {
     struct snd_soc_component *component = dai->component;
     
     if (mute) {
         if (!SABRE9018Q2C_isMuted) {
             SABRE9018Q2C_VOLUME1 = snd_soc_component_read(component, ES9018K2M_VOLUME1);
             SABRE9018Q2C_VOLUME2 = snd_soc_component_read(component, ES9018K2M_VOLUME2);
             SABRE9018Q2C_isMuted = true;
         }
         snd_soc_component_write(component, ES9018K2M_VOLUME1, 0xFF);
         snd_soc_component_write(component, ES9018K2M_VOLUME2, 0xFF);
     }
     return 0;
 }
 
 static int es9018k2m_unmute(struct snd_soc_dai *dai)
 {
    struct snd_soc_component *component = dai->component; 
    snd_soc_component_write(component, ES9018K2M_VOLUME1, SABRE9018Q2C_VOLUME1);
    snd_soc_component_write(component, ES9018K2M_VOLUME2, SABRE9018Q2C_VOLUME2);
    SABRE9018Q2C_isMuted = false;
    return 0;
 }

 /* Volume Scale */
 static const DECLARE_TLV_DB_SCALE(volume_tlv, -12750, 50, 1);
 

 static const uint32_t es9018k2m_dai_rates_master[] = {
    44100, 48000, 88200, 96000, 176400, 192000
};

 static const struct snd_pcm_hw_constraint_list constraints_master = {
    .list  = es9018k2m_dai_rates_master,
    .count = ARRAY_SIZE(es9018k2m_dai_rates_master),
 };

 static const uint32_t es9018k2m_dai_rates_slave[] = {
	8000, 11025, 16000, 22050, 32000,
	44100, 48000, 64000, 88200, 96000, 176400, 192000, 352800, 384000
};

static const struct snd_pcm_hw_constraint_list constraints_slave = {
    .list  = es9018k2m_dai_rates_slave,
    .count = ARRAY_SIZE(es9018k2m_dai_rates_slave),
};

/* i2s/spdif selection*/

static const char * const es9018k2m_input_texts[] = {
    "I2S",
    "SPDIF"
};

static const unsigned int es9018k2m_input_values[] = {
    0x00,  // I2S (bit 0 cleared)
    0x01   // SPDIF (bit 0 set)
};

static SOC_ENUM_SINGLE_DECL(es9018k2m_input_enum,
    ES9018K2M_INPUT_SELECT, 0, es9018k2m_input_texts);

/* FIR Filter Options */

static const char * const es9018k2m_filter_texts[] = {
    "Slow Roll Off",
    "Fast Roll Off",
    "Minimum Phase", 
    "Bypass Oversampling"
};

static const unsigned int es9018k2m_filter_values[] = {
    0,  // Slow Roll Off
    1,  // Fast Roll Off
    2,  // Minimum Phase
    3   // Bypass Oversampling
};

static const struct soc_enum es9018k2m_filter_enum =
    SOC_ENUM_SINGLE(0, 0, ARRAY_SIZE(es9018k2m_filter_texts),
                   es9018k2m_filter_texts);

/* IIR Filter Options */
static const char * const es9018k2m_iir_texts[] = {
    "47K (PCM)",
    "50K (DSD)",
    "60K (DSD)", 
    "70K (DSD)",
    "Bypass"
};

static const unsigned int es9018k2m_iir_values[] = {0, 1, 2, 3, 4};

static const struct soc_enum es9018k2m_iir_enum =
    SOC_ENUM_SINGLE(0, 0, ARRAY_SIZE(es9018k2m_iir_texts),
                   es9018k2m_iir_texts);

/* Deemphasis Options */
static const char * const es9018k2m_deemphasis_texts[] = {
    "Off",
    "32K",
    "44.1K",
    "48K"
};

static const unsigned int es9018k2m_deemphasis_values[] = {
    0x4A,  // Off
    0x0A,  // 32K
    0x1A,  // 44.1K
    0x2A   // 48K
};

static const struct soc_enum es9018k2m_deemphasis_enum =
    SOC_ENUM_SINGLE(0, 0, ARRAY_SIZE(es9018k2m_deemphasis_texts),
                   es9018k2m_deemphasis_texts);


/* I2S DPLL Options (upper nibble) */
static const char * const es9018k2m_i2s_dpll_texts[] = {
    "00", "01", "02", "03", "04", "05", "06", "07",
    "08", "09", "10", "11", "12", "13", "14", "15"
};

/* DSD DPLL Options (lower nibble) */ 
static const char * const es9018k2m_dsd_dpll_texts[] = {
    "09", "10", "11", "12", "13", "14", "15"
};

static const unsigned int es9018k2m_dsd_dpll_values[] = {
    0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F
};

static SOC_ENUM_SINGLE_DECL(es9018k2m_i2s_dpll_enum,
    ES9018K2M_DPLL, 4, es9018k2m_i2s_dpll_texts);

static SOC_ENUM_SINGLE_DECL(es9018k2m_dsd_dpll_enum,
    ES9018K2M_DPLL, 0, es9018k2m_dsd_dpll_texts);

/* DAI operations */
static int es9018k2m_dai_startup_master(struct snd_pcm_substream *substream,
    struct snd_soc_dai *dai)
{
return snd_pcm_hw_constraint_list(substream->runtime, 0,
SNDRV_PCM_HW_PARAM_RATE, &constraints_master);
}

static int es9018k2m_dai_startup_slave(struct snd_pcm_substream *substream,
   struct snd_soc_dai *dai)
{
return snd_pcm_hw_constraint_list(substream->runtime, 0,
SNDRV_PCM_HW_PARAM_RATE, &constraints_slave);
}

static int es9018k2m_dai_startup(struct snd_pcm_substream *substream,struct snd_soc_dai *dai)
{
    struct es9018k2m_priv *priv = snd_soc_component_get_drvdata(dai->component);

    es9018k2m_mute(dai, 1, SNDRV_PCM_STREAM_PLAYBACK);

    switch (priv->fmt & SND_SOC_DAIFMT_MASTER_MASK) {
    case SND_SOC_DAIFMT_CBM_CFM:
        return es9018k2m_dai_startup_master(substream, dai);
    case SND_SOC_DAIFMT_CBS_CFS:
        return es9018k2m_dai_startup_slave(substream, dai);
    default:
        return -EINVAL;
    }
}

static void es9018k2m_shutdown(struct snd_pcm_substream *substream,
    struct snd_soc_dai *dai)
{
    es9018k2m_mute(dai, 1, SNDRV_PCM_STREAM_PLAYBACK);
}
 

static int es9018k2m_dai_trigger(struct snd_pcm_substream *substream, int cmd, struct snd_soc_dai *dai)
{
	int ret = 0;
	switch(cmd)
	{
		case SNDRV_PCM_TRIGGER_START:
		case SNDRV_PCM_TRIGGER_RESUME:
		case SNDRV_PCM_TRIGGER_PAUSE_RELEASE:
			mdelay(100);   // reduced to 100 from 1500 ms
			es9018k2m_unmute(dai);
			break;
		case SNDRV_PCM_TRIGGER_STOP:
		case SNDRV_PCM_TRIGGER_SUSPEND:
		case SNDRV_PCM_TRIGGER_PAUSE_PUSH:
			es9018k2m_mute(dai, 1, SNDRV_PCM_STREAM_PLAYBACK);
			break;
		default:
			ret = -EINVAL;
			break;
	}
	return ret;
}

 static int es9018k2m_hw_params(struct snd_pcm_substream *substream,
                               struct snd_pcm_hw_params *params,
                               struct snd_soc_dai *dai)
 {
     struct snd_soc_component *component = dai->component;
     unsigned int iface = snd_soc_component_read(component, ES9018K2M_INPUT_CONFIG) & 0x3f;
 
     switch (params_format(params)) {
         case SNDRV_PCM_FORMAT_S16_LE:
             iface |= 0x0;
             break;
         case SNDRV_PCM_FORMAT_S24_LE:
         case SNDRV_PCM_FORMAT_S32_LE:
             iface |= 0x80;
             break;
         default:
             return -EINVAL;
     }
 
     snd_soc_component_write(component, ES9018K2M_INPUT_CONFIG, iface);
     return 0;
 }
 

static int es9018k2m_set_fmt(struct snd_soc_dai *dai, unsigned int fmt)
 {
    struct es9018k2m_priv *priv = snd_soc_component_get_drvdata(dai->component);

    /* Validate interface format */
    switch (fmt & SND_SOC_DAIFMT_FORMAT_MASK) {
    case SND_SOC_DAIFMT_I2S:
    case SND_SOC_DAIFMT_RIGHT_J:
    case SND_SOC_DAIFMT_LEFT_J:
        break;
    default:
        return -EINVAL;
    }

    /* Store format */
    priv->fmt = fmt;
    return 0;
 }


static int es9018k2m_input_get(struct snd_kcontrol *kcontrol,
    struct snd_ctl_elem_value *ucontrol)
{
struct snd_soc_component *component = snd_kcontrol_chip(kcontrol);
unsigned int reg = snd_soc_component_read(component, ES9018K2M_INPUT_SELECT);
ucontrol->value.enumerated.item[0] = (reg & 0x01);
return 0;
}

static int es9018k2m_input_put(struct snd_kcontrol *kcontrol,
    struct snd_ctl_elem_value *ucontrol)
{
struct snd_soc_component *component = snd_kcontrol_chip(kcontrol);
unsigned int value = ucontrol->value.enumerated.item[0];
unsigned int reg = snd_soc_component_read(component, ES9018K2M_INPUT_SELECT);

/* Preserve other bits (7:1) while setting input selection */
reg &= ~(0x01);  // Clear bit 0
reg |= (value & 0x01);

snd_soc_component_write(component, ES9018K2M_INPUT_SELECT, reg);
return 0;
}

/* Custom get/put functions */
static int es9018k2m_filter_get(struct snd_kcontrol *kcontrol,
    struct snd_ctl_elem_value *ucontrol)
{
struct snd_soc_component *component = snd_kcontrol_chip(kcontrol);
unsigned int reg7 = snd_soc_component_read(component, ES9018K2M_GENERAL_SET);
unsigned int reg21 = snd_soc_component_read(component,ES9018K2M_INPUT_SELECT);

if (reg21 & 0x01) {
ucontrol->value.enumerated.item[0] = 3; // Bypass Oversampling
} else if (reg7 & (1 << 5)) {
ucontrol->value.enumerated.item[0] = 0; // Slow Roll Off
} else if (reg7 & (1 << 6)) {
ucontrol->value.enumerated.item[0] = 2; // Minimum Phase
} else {
ucontrol->value.enumerated.item[0] = 1; // Fast Roll Off
}

return 0;
}

static int es9018k2m_filter_put(struct snd_kcontrol *kcontrol,
    struct snd_ctl_elem_value *ucontrol)
{
struct snd_soc_component *component = snd_kcontrol_chip(kcontrol);
unsigned int value = ucontrol->value.enumerated.item[0];
unsigned int reg7 = snd_soc_component_read(component, ES9018K2M_GENERAL_SET);
unsigned int reg21 = snd_soc_component_read(component,ES9018K2M_INPUT_SELECT);

/* Preserve other bits in registers */
reg7 &= ~((1 << 5) | (1 << 6));  // Clear filter control bits
reg21 &= ~(1 << 0);              // Clear OSF bypass bit

switch (value) {
case 0: // FIR_SLOW_ROLL_OFF
reg7 |= (1 << 5);
break;
case 1:  // FIR_FAST_ROLL_OFF
/* Bits already cleared */
break;
case 2: //FIR_MINIMUM_PHASE
reg7 |= (1 << 6);
break;
case 3: // FIR_BYPASS_OSF
reg21 |= (1 << 0);
break;
default:
return -EINVAL;
}

snd_soc_component_write(component, ES9018K2M_GENERAL_SET, reg7);
snd_soc_component_write(component, ES9018K2M_INPUT_SELECT, reg21);

return 0;
}
/* iir functions*/

static int es9018k2m_iir_get(struct snd_kcontrol *kcontrol,
    struct snd_ctl_elem_value *ucontrol)
{
struct snd_soc_component *component = snd_kcontrol_chip(kcontrol);
unsigned int reg7 = snd_soc_component_read(component, ES9018K2M_GENERAL_SET);
unsigned int reg21 = snd_soc_component_read(component, ES9018K2M_INPUT_SELECT);

if (reg21 & (1 << 2)) {
ucontrol->value.enumerated.item[0] = 4; // Bypass
} else {
ucontrol->value.enumerated.item[0] = ((reg7 >> 2) & 0x3); // Get bits 2-3
}

return 0;
}

static int es9018k2m_iir_put(struct snd_kcontrol *kcontrol,
    struct snd_ctl_elem_value *ucontrol)
{
struct snd_soc_component *component = snd_kcontrol_chip(kcontrol);
unsigned int value = ucontrol->value.enumerated.item[0];
unsigned int reg7 = snd_soc_component_read(component, ES9018K2M_GENERAL_SET);
unsigned int reg21 = snd_soc_component_read(component, ES9018K2M_INPUT_SELECT);

/* Clear relevant bits */
reg7 &= ~(0x3 << 2);
reg21 &= ~(1 << 2);

switch (value) {
case 0: // 47K (PCM)
break;
case 1: // 50K (DSD)
reg7 |= (1 << 2);
break;
case 2: // 60K (DSD)
reg7 |= (1 << 3);
break;
case 3: // 70K (DSD)
reg7 |= (0x3 << 2);
break;
case 4: // Bypass
reg21 |= (1 << 2);
break;
default:
return -EINVAL;
}

snd_soc_component_write(component, ES9018K2M_GENERAL_SET, reg7);
snd_soc_component_write(component, ES9018K2M_INPUT_SELECT, reg21);

return 0;
}

/* deempasis functions */

static int es9018k2m_deemphasis_get(struct snd_kcontrol *kcontrol,
    struct snd_ctl_elem_value *ucontrol)
{
struct snd_soc_component *component = snd_kcontrol_chip(kcontrol);
unsigned int reg = snd_soc_component_read(component, ES9018K2M_DEEMPHASIS);

switch (reg) {
case 0x4A: ucontrol->value.enumerated.item[0] = 0; break; // Off
case 0x0A: ucontrol->value.enumerated.item[0] = 1; break; // 32K
case 0x1A: ucontrol->value.enumerated.item[0] = 2; break; // 44.1K
case 0x2A: ucontrol->value.enumerated.item[0] = 3; break; // 48K
default:   ucontrol->value.enumerated.item[0] = 0; break; // Default to Off
}

return 0;
}

static int es9018k2m_deemphasis_put(struct snd_kcontrol *kcontrol,
    struct snd_ctl_elem_value *ucontrol)
{
struct snd_soc_component *component = snd_kcontrol_chip(kcontrol);
unsigned int value = ucontrol->value.enumerated.item[0];

if (value >= ARRAY_SIZE(es9018k2m_deemphasis_values))
return -EINVAL;

snd_soc_component_write(component, ES9018K2M_DEEMPHASIS,
es9018k2m_deemphasis_values[value]);

return 0;
}

/* I2S DPLL Control */
static int es9018k2m_i2s_dpll_get(struct snd_kcontrol *kcontrol,
    struct snd_ctl_elem_value *ucontrol)
{
struct snd_soc_component *component = snd_kcontrol_chip(kcontrol);
unsigned int reg = snd_soc_component_read(component, ES9018K2M_DPLL);
ucontrol->value.enumerated.item[0] = (reg >> 4) & 0x0F;
return 0;
}

static int es9018k2m_i2s_dpll_put(struct snd_kcontrol *kcontrol,
    struct snd_ctl_elem_value *ucontrol)
{
struct snd_soc_component *component = snd_kcontrol_chip(kcontrol);
unsigned int value = ucontrol->value.enumerated.item[0];
unsigned int reg = snd_soc_component_read(component, ES9018K2M_DPLL);

reg &= ~(0xF0); // Clear upper nibble
reg |= (value << 4);

snd_soc_component_write(component, ES9018K2M_DPLL, reg);
return 0;
}

/* DSD DPLL Control */
static int es9018k2m_dsd_dpll_get(struct snd_kcontrol *kcontrol,
    struct snd_ctl_elem_value *ucontrol)
{
struct snd_soc_component *component = snd_kcontrol_chip(kcontrol);
unsigned int reg = snd_soc_component_read(component, ES9018K2M_DPLL);
unsigned int dsd_val = reg & 0x0F;
int i;

for (i = 0; i < ARRAY_SIZE(es9018k2m_dsd_dpll_values); i++) {
if (es9018k2m_dsd_dpll_values[i] == dsd_val) {
ucontrol->value.enumerated.item[0] = i;
break;
}
}
return 0;
}

static int es9018k2m_dsd_dpll_put(struct snd_kcontrol *kcontrol,
    struct snd_ctl_elem_value *ucontrol)
{
struct snd_soc_component *component = snd_kcontrol_chip(kcontrol);
unsigned int value = ucontrol->value.enumerated.item[0];
unsigned int reg = snd_soc_component_read(component, ES9018K2M_DPLL);

if (value >= ARRAY_SIZE(es9018k2m_dsd_dpll_values))
return -EINVAL;

reg &= ~(0x0F); // Clear lower nibble
reg |= es9018k2m_dsd_dpll_values[value];

snd_soc_component_write(component, ES9018K2M_DPLL, reg);
return 0;
}

/* Controlss */
static const struct snd_kcontrol_new es9018k2m_controls[] = {
    SOC_DOUBLE_R_TLV("Digital Playback Volume", ES9018K2M_VOLUME1, ES9018K2M_VOLUME2,
                     0, 255, 1, volume_tlv),
    SOC_ENUM_EXT("FIR Filter", es9018k2m_filter_enum,
                        es9018k2m_filter_get, es9018k2m_filter_put),
    SOC_ENUM_EXT("IIR Filter", es9018k2m_iir_enum,
                        es9018k2m_iir_get, es9018k2m_iir_put),
    SOC_ENUM_EXT("Deemphasis Filter", es9018k2m_deemphasis_enum,
                        es9018k2m_deemphasis_get, es9018k2m_deemphasis_put),
    SOC_ENUM_EXT("I2S DPLL Bandwidth", es9018k2m_i2s_dpll_enum,
                        es9018k2m_i2s_dpll_get, es9018k2m_i2s_dpll_put),
    SOC_ENUM_EXT("DSD DPLL Bandwidth", es9018k2m_dsd_dpll_enum,
                        es9018k2m_dsd_dpll_get, es9018k2m_dsd_dpll_put),
    SOC_ENUM_EXT("I2S/SPDIF Input", es9018k2m_input_enum,
                        es9018k2m_input_get, es9018k2m_input_put),

};

 static const struct snd_soc_dai_ops es9018k2m_dai_ops = {
    .startup    = es9018k2m_dai_startup,
    .shutdown   = es9018k2m_shutdown,
    .hw_params  = es9018k2m_hw_params,
    .set_fmt    = es9018k2m_set_fmt,
    .mute_stream = es9018k2m_mute,
    .trigger = es9018k2m_dai_trigger,
 };
 

 static struct snd_soc_dai_driver es9018k2m_dai = {
    .name = "es9018k2m-hifi",
    .playback = {
        .stream_name    = "Playback",
        .channels_min   = 2,
        .channels_max   = 2,
        .rates          = SNDRV_PCM_RATE_CONTINUOUS,
        .rate_min       = 8000,
        .rate_max       = 384000,
        .formats        = SNDRV_PCM_FMTBIT_S16_LE |
                          SNDRV_PCM_FMTBIT_S24_LE |
                          SNDRV_PCM_FMTBIT_S32_LE,
    },
    .ops = &es9018k2m_dai_ops,
 };
 
static const struct snd_soc_component_driver es9018k2m_component_driver = {
    .controls = es9018k2m_controls,
    .num_controls = ARRAY_SIZE(es9018k2m_controls),
    .idle_bias_on = 1,
    .use_pmdown_time = 1,
    .endianness = 1,
 };

 static const struct regmap_config es9018k2m_regmap = {
     .reg_bits = 8,
     .val_bits = 8,
     .max_register = 93,
     .reg_defaults = es9018k2m_reg_defaults,
     .num_reg_defaults = ARRAY_SIZE(es9018k2m_reg_defaults),
     .writeable_reg = es9018k2m_writeable,
     .readable_reg = es9018k2m_readable,
     .volatile_reg = es9018k2m_volatile,
     .cache_type = REGCACHE_RBTREE,
 };
 
 static int es9018k2m_probe(struct i2c_client *i2c)
{
    struct es9018k2m_priv *priv;
    struct regmap *regmap;
    
    priv = devm_kzalloc(&i2c->dev, sizeof(*priv), GFP_KERNEL);
    if (!priv)
        return -ENOMEM;

    regmap = devm_regmap_init_i2c(i2c, &es9018k2m_regmap);
    if (IS_ERR(regmap))
        return PTR_ERR(regmap);

    priv->regmap = regmap;
    i2c_set_clientdata(i2c, priv);

    return devm_snd_soc_register_component(&i2c->dev,
            &es9018k2m_component_driver, &es9018k2m_dai, 1);
}
 
/* I2C driver configuration */

 static const struct i2c_device_id es9018k2m_i2c_id[] = {
     { "es9018k2m", 0 },
     { }
 };
 MODULE_DEVICE_TABLE(i2c, es9018k2m_i2c_id);
 
 static const struct of_device_id es9018k2m_of_match[] = {
     { .compatible = "ess,es9018k2m", },
     { }
 };

 MODULE_DEVICE_TABLE(of, es9018k2m_of_match);
 
 static struct i2c_driver es9018k2m_i2c_driver = {
     .driver = {
         .name = "es9018k2m",
         .of_match_table = es9018k2m_of_match,
     },
     .probe = es9018k2m_probe,
     .id_table = es9018k2m_i2c_id,
 };
 
 module_i2c_driver(es9018k2m_i2c_driver);
 
 MODULE_DESCRIPTION("ASoC ES9018K2M driver");
 MODULE_AUTHOR("Satoru Kawase <satoru.kawase@gmail.com>");
 MODULE_LICENSE("GPL");
