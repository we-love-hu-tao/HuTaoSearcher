# Hu Tao Art Searcher
# Copyright (C) 2024  F1zzTao

# This file is part of Hu Tao Art Searcher.
# Hu Tao Art Searcher is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Hu Tao Art Searcher.  If not, see <https://www.gnu.org/licenses/>.

# You may contact F1zzTao by this email address: timurbogdanov2008@gmail.com

import os

from dotenv import load_dotenv

load_dotenv()

# Group ID must be positive
GROUP_ID = 193964161
ADMIN_IDS = (322615766, 504114608,)

HU_TAO_QUERY = 'hu_tao_(genshin_impact) -animated -rating:e'
RERUN_DAY_SEARCH_RE = r'(\d+) день без рерана'
HU_TAO_RUSSIAN_TAG = 'ХуТао'
CHARACTER_RENAMINGS = {
    "KamisatoAyaka": "Ayaka",
    "KamisatoAyato": "Ayato",
    "KaedeharaKazuha": "Kazuha",
    "KujouSara": "Sara",
    "SangonomiyaKokomi": "Kokomi",
    "ShikanoinHeizou": "Heizou",
}

DB_PATH = './db.db'

VK_API_TOKEN = os.getenv('VK_API_TOKEN')
VK_USER_API_TOKEN = os.getenv('VK_USER_API_TOKEN')
