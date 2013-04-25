@rem Copyright (c) 2011-2013 Turbulenz Limited
@echo off
@rem Convert Bitmap Font Generator data (.fnt) files into a Turbulenz JSON asset.
@rem http://www.angelcode.com/products/bmfont/

@python -m turbulenz_tools.tools.bmfont2json %*
