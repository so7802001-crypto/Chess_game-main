# ♟️ Intelligent Python Chess AI

An advanced Chess Engine built with **Python** and **Pygame**, featuring a smart AI opponent powered by **NegaMax**, **Alpha-Beta Pruning**, **Transposition Tables**, and an **Opening Book**.

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Installation](#-installation)
- [How to Play](#-how-to-play)
- [Project Structure](#-project-structure)
- [Technical Details](#-technical-details)
- [Author](#-author)

---

## 🧐 Overview

This project is a fully functional chess engine developed as an AI coursework project. It demonstrates the implementation of classic Game Theory algorithms combined with modern software engineering practices. The engine supports **Human vs. Human** and **Human vs. AI** modes, featuring a sophisticated AI that uses memory optimization (Transposition Tables) and pre-calculated opening strategies (e.g., Napoleon's Plan) to play at a high level.

---

## ✨ Key Features

### 🧠 Advanced AI
- **Search Algorithm:** Uses **NegaMax** (Minimax variant) with **Alpha-Beta Pruning** for deep calculation.
- **Memory Optimization:** Implements **Transposition Tables** (Hashing) to remember previously evaluated board positions, drastically reducing computation time.
- **Opening Book:** The AI possesses "knowledge" of famous openings:
  - **White:** Executes **Napoleon's Plan (Scholar's Mate)** if allowed.
  - **Black:** Plays classic central defense logic.
- **Smart Move Ordering:** Prioritizes captures using **MVV-LVA** (Most Valuable Victim - Least Valuable Aggressor) to maximize pruning efficiency.

### 🎮 Game Modes & Interface
- **Multi-Stage Menu:**
  1. Select Mode (**PvP** or **Player vs AI**).
  2. Select Side (**White** or **Black**).
  3. Select Difficulty (**Easy**, **Medium**, **Hard**).
- **Interactive GUI:** Piece highlighting, legal move suggestions, and smooth animations.
- **Pawn Promotion:** Interactive selection menu for human players (Auto-Queen for AI).

### ⚙️ Complete Chess Logic
- **Rule Compliance:** Handles **Castling**, **En Passant**, **Pawn Promotion**, and **Pins/Checks**.
- **Stalemate Detection:** Automatically detects draws via **Threefold Repetition** or insufficient material.
- **Multiprocessing:** The AI runs on a separate process to ensure the UI remains responsive while the computer thinks.

---

## 📥 Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/noran66/Chess_game.git](https://github.com/noran66/Chess_game.git)
    cd Chess_game
    ```

2.  **Install dependencies:**
    This project requires `pygame`.
    ```bash
    pip install pygame
    ```

3.  **Run the Game:**
    ```bash
    python main.py
    ```

---

## 🎮 How to Play

1.  **Menu Navigation:**
    - **Step 1:** Choose **PvP** (Human vs Human) or **Player vs AI**.
    - **Step 2:** (If vs AI) Choose your color (**White** or **Black**).
    - **Step 3:** Choose Difficulty (determines AI search depth).
2.  **Gameplay:**
    - Click on a piece to view valid moves (highlighted in yellow).
    - Click on a target square to move (captures highlighted in red).
3.  **Controls:**
    - **`Z` Key:** Undo the last move.
    - **`R` Key:** Reset the game and return to the Main Menu.

---

## 📂 Project Structure

The project follows a modular architecture:

```text
Chess_Project/
│
├── main.py                # Entry point, GUI, Menu Logic & Multiprocessing
├── config.py              # Global constants (Dimensions, Colors, Depth settings)
│
├── Engine/                # Core Logic Module
│   ├── gameState.py       # Board representation, Move validation, History log
│   └── move.py            # Move class & Chess notation
│
├── AI/                    # Intelligence Module
│   ├── moveFinder.py      # Search Algorithms (NegaMax), Opening Book, Transposition Table
│   └── evaluation.py      # Static Evaluation (Material & Piece-Square Tables)
│
└── images/                # Asset folder (.png files)
🧠 Technical Details
The Engine
Board Representation: 8x8 2D List.

Anti-Loop Logic: Uses a boardHistory list to detect 3-fold repetition and enforce Stalemate.

The AI Architecture
Algorithm: Recursive NegaMax with Alpha-Beta Pruning.

Optimization (The "Brain"):

Transposition Table: Uses a dictionary to map board hash keys to scores. If a position repeats, the score is retrieved instantly (Memoization).

Move Ordering: Sorts moves before searching to increase the likelihood of early cut-offs.

Knowledge (The "Book"):

Hardcoded logic for the first ~4 moves to simulate professional play styles without calculating.

👤 Author
Developed by Noran

Department: AI

Class: 2027

Language: Python 3.9.13