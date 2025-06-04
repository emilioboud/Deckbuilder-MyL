# Mitos y Leyendas Deck Builder

A desktop GUI application (written in Python/Tkinter) to build, visualize, and analyze decks for the **Mitos y Leyendas** trading card game.  
Features include:

- **Drag-and-drop-style deck display** with overlapping card images  
- **Category summary** (Aliados, Armas, Talismanes, Totems, Oros, Total)  
- **Mana curve histogram** (cost 1–6, color‐coded by category)  
- **Consistency calculator** that computes odds of drawing key combinations under:  
  1. A single 8‐card draw  
  2. An “8 → 7” mulligan (one mulligan)  
  3. An “8 → 7 → 6” mulligan (two mulligans)  
- **Random hand dealer** with “Deal Hand” / “Mulligan” buttons, plus a “1000 Hands” simulator  
- **Save** / **Import** deck (.txt) support  
- Click any card image in the deck display to **add/remove** copies  
- Deck import via a dropdown menu listing all .txt files in the `decks/` folder  
- Built-in enforcement of **max 50 cards** per deck  

---

## Folder Structure

  deckbuilder/  
    card_data/                  ← One “.txt” per card (metadata)  
      sisifo.txt                ← e.g. [1, 5, "Aliados"]  
      oro.txt                   ← ["Oros"]  
      …  
    card_images/                ← One “.png” (or “.jpg”) per card  
      sisifo.png  
      oro.png  
      …  
    decks/                      ← Saved deck lists (.txt) created by “Save Deck”  
      MyDeckName.txt  
    one_use_scripts/            ← Utility scripts (e.g. exe generator, icon installer)  
      …  
    build/                      ← PyInstaller (or similar) build output  
      …  
    dist/                       ← “dist” folder for executables (if any)  
      …  
    main.py                     ← Main application source  
    requirements.txt            ← Dependencies (e.g. Pillow)  
    Deckbuilder_icon.ico        ← Application icon for .vbs/shortcut  
    Mitos y Leyendas - Deckbuilder.vbs  
                                 ← Windows .vbs stub to launch main.py without console  
    main.spec                   ← PyInstaller spec file (if used)  
    README.md                   ← This file  
    .gitignore                  ← Common Python/Git ignores  

---

## Prerequisites

1. **Python 3.7+** (tested on 3.10/3.11/3.13)  
2. **Pillow** (for loading and resizing card images)  
   Run in terminal:  
     pip install Pillow  
3. A working copy of this repository (either clone from GitHub or download ZIP).  
4. Ensure your `card_data/` and `card_images/` folders are populated (see next section).

---

## Card Data & Images

- **card_data/**  
  Each card must have a corresponding `.txt` file named exactly after the card (e.g. `sisifo.txt`, `oro.txt`). The file contents must follow one of these formats:  
  1. `["Oros"]`  
     - Used for Oros cards (these count only in the “Oros” tally; they do not contribute to mana curve).  
  2. `[cost, "Category"]`  
     - For Armas, Talismanes, or Totems (no strength value).  
     - Example: `[3, "Armas"]`  
  3. `[cost, strength, "Category"]`  
     - For Aliados (cards with both cost and strength).  
     - Example: `[1, 5, "Aliados"]`

- **card_images/**  
  Each card must have a corresponding image file named `<card_name>.png` (or `.jpg`). The filename (minus extension) must exactly match its `.txt` in `card_data/`, case‐insensitive.  

---

## How to Run

1. Open a terminal (PowerShell, Git Bash, CMD, etc.).  
2. Change directory to the project folder where `main.py` lives. For example:  
     cd E:\Scripts\deckbuilder  
3. Install dependencies if you haven’t already:  
     pip install Pillow  
4. Launch the GUI:  
     python main.py  
5. (Optional) If you prefer to run without a console window, double‐click the provided `Mitos y Leyendas - Deckbuilder.vbs` file.  

---

## Usage Overview

### 1. Deck Display (Top-Left)

- A cream‐colored Canvas shows overlapping card images in rows.  
- Sorting order for non-Oros cards:  
  1. Category priority: Aliados → Armas → Talismanes → Totems → Oros  
  2. Cost (ascending; Oros have no cost → treated as very large cost)  
  3. Name (alphabetical)  
- Overlap rules:  
  - **Same name** overlaps by 20px horizontally.  
  - **Same category, different name** overlaps by 30px.  
  - **Different category**: start a new block (no overlap).  
- **All Oros** cards are forced onto a new bottom row:  
  - Except for the special card named “oro” (lowercase), which is displayed once, followed by text “xN” indicating total Oros count.  
- **Click interactions**:  
  - **Left‐click** on a card image removes one copy (down to zero).  
  - **Right‐click** on a card image adds one copy (up to the 50-card limit).  

### 2. Category Summary (Top-Right)

Displays counts for each category and total:  
  Aliados: ___  
  Armas: ___  
  Talismanes: ___  
  Totems: ___  
  Oros: ___  
  Total: ___  

These update automatically whenever the deck changes.

### 3. Mana Curve (Below Deck Display)

A stacked‐bar histogram showing costs 1 through 6.  
- Each column (cost) is subdivided by category colors:  
  - Aliados → Orange (#FFA500)  
  - Talismanes → Light Blue (#ADD8E6)  
  - Totems → Dark Green (#006400)  
  - Armas → Purple (#800080)  
- The top of each column shows the total number of cards at that cost (in bold).  
- Peak height is 20 segments, each segment = 1 card.  
- Oros cards are excluded from the mana curve entirely.

### 4. Bottom Menu (Cards / Save / Import / Quit)

#### Card Entry

- **Card name:** Type (or type‐and‐autocomplete) the exact card name (no extension).  
- **Quantity:** Enter how many copies to add or remove.  
- **Add Card** button: Adds up to that many copies (will truncate at 50 total cards and show a popup).  
- **Remove Card** button: Removes up to that many copies (if you remove more than exist, it simply removes all copies).  

#### Save / Import Deck

- **Save as:** Enter a filename (no “.txt”) and click **Save Deck**.  
  - This writes a file to `decks/<filename>.txt` in the format:  
      3xsisifo  
      2xantorchaolimpica  
      …  
- **Import deck:** Select from a dropdown of all `.txt` files inside `decks/`. Click **Import Deck** to replace the current deck.  
  - If a deck file has more than 50 cards total, it will import only the first 50 and show a warning.  

#### Quit

- **Quit** button: Closes the application.

### 5. Consistency Panel (Right-Top)

Calculates and displays **combined odds** for three drawing scenarios:

1. **“8-card draw”** (no mulligan)  
2. **“8 → 7 mulligan”** (one mulligan)  
3. **“8 → 7 → 6 mulligan”** (two mulligans)  

Each column shows four lines:  
  P(≥2 Oros): ___%  
  P(≥3 Oros): ___%  
  P(≥1 2-cost Aliados): ___%  
  Avg cost: ___  

Mathematically:  
  Let P₈(X) = probability of event X in a single 8-card draw.  
  Let P₇(X) = probability of event X in a single 7-card draw.  
  Let P₆(X) = probability of event X in a single 6-card draw.  

- **Column 1 (8-card):** P₈ only.  
- **Column 2 (8→7):** P₈ + (1 – P₈)·P₇.  
- **Column 3 (8→7→6):** P₈ + (1 – P₈)·P₇ + (1 – P₈)·(1 – P₇)·P₆.  

Here X can be “≥2 Oros,” “≥3 Oros,” or “≥1 Aliados with cost=2.”  
The “Avg cost” line simply computes the average cost of all non‐Oros cards in the 50-card deck.

### 6. Random Hand Dealer (Right-Middle)

- **Deal Hand**: Draw 8 random cards from a 50-card deck.  
- **Mulligan**: If a hand exists, shuffle those cards back in and draw one fewer card (down to a minimum of 1).  
- Displays the hand in a 2×4 grid (two rows of 4).  
- **Next to the first row of cards**, it shows a small info box with:  
    Aliados: <count>  
    Oros: <count>  
    Soporte: <count>   (where Soporte = Armas + Totems + Talismanes)  

- **Below** the second row of cards, a status line displays three items in one row:  
  2 Oros Deal Hand Mulligan Turn 1 play  

  - **“2 Oros”** (bold): Turns **green** if the current hand has ≥2 Oros, else **red**.  
  - **Deal Hand** button  
  - **Mulligan** button  
  - **“Turn 1 play”** (bold): Turns **green** if the current hand contains at least one Aliado with cost 1 or 2, else **red**.

### 7. “1000 Hands” Simulator (Right-Bottom)

- Next to the second row of dealt cards, there is a **“1000 Hands”** button. Clicking this runs 1000 simulated 8-card draws (with no mulligans) from the current 50-card deck and counts:  
  • Hands ≥2 Oros  
  • Hands Turn1 Play (≥1 Aliado cost 1 or 2)  
  • Great hands (both conditions met)  
- The results appear in a small box immediately under the “1000 Hands” button.

---

## Building an Executable (Optional)

If you want to distribute a standalone Windows executable:

1. **Install PyInstaller**:  
     pip install pyinstaller  
2. Run (from the project root):  
     pyinstaller --onefile --add-data "card_data;card_data" --add-data "card_images;card_images" --icon=Deckbuilder_icon.ico main.py  
   - Use semicolons (`;`) between source and target on Windows.  
   - This produces `dist/main.exe`, which bundles `main.py`, the two data folders, and the Pillow library.  
3. Copy `main.exe` into the same folder as your `card_data/` and `card_images/` (if not already bundled). Double-click to run.  
4. (Optional) Launch via the provided `Mitos y Leyendas - Deckbuilder.vbs` to run without a console window.

---

## GitHub Repository

Source code is hosted at:  
https://github.com/emilioboud/Deckbuilder-MyL  

Feel free to fork, open issues, and submit pull requests!

---

## License

*(Example: MIT License)*

MIT License

Copyright (c) 2025 Emilio Boud

Permission is hereby granted, free of charge, to any person obtaining a copy  
of this software and associated documentation files (the “Software”), to deal  
in the Software without restriction, including without limitation the rights  
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell  
copies of the Software, and to permit persons to whom the Software is  
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all  
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR  
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,  
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE  
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER  
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,  
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE  
SOFTWARE.

---

## Acknowledgments

- **Pillow (PIL)** for image loading and resizing  
- **Tkinter** for the GUI framework  
- The **Mitos y Leyendas** community for providing card data and images  

Enjoy building your Mitos y Leyendas decks!
