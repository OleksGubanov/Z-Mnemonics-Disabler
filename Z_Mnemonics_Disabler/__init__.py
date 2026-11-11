# SPDX-License-Identifier: GPL-3.0-only

"""Register Z Mnemonics Disabler with Krita."""

from krita import Krita

from .main import ZMnemonicsExtension

Krita.instance().addExtension(ZMnemonicsExtension(Krita.instance()))
