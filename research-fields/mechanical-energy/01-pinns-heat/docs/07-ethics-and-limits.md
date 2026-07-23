# 07 — 倫理・限界

## PINN の失敗モード

PINN は **万能ではありません**。以下のケースで系統的に失敗することが知られています:

- **高周波数解 / スペクトル bias**: MLP は低周波数を先に学習し、高周波数成分が残る (Rahaman et al., 2019)
- **多スケール問題**: 熱伝導率が場所で桁違いに変わるケースでは学習が停滞
- **時間発展の長期予測**: t が大きくなるほど誤差が蓄積
- **境界条件の柔らかい適用**: BC を損失で強制するため、厳密には守られない (Hard constraint / distance function 方式もある)

参考: Krishnapriyan et al., *"Characterizing possible failure modes in physics-informed neural networks"*, NeurIPS 2021.

## 実務への転用時の注意

- **CFD, 構造解析等の意思決定に PINN 単独で用いるのは危険**。必ず既存 solver (FEM / FVM / FDM) の結果と比較検証してください
- **安全性が問われる用途** (原子力、航空、医療機器等) では、PINN は探索/前処理用途に限定し、認証プロセスを持つ solver を最終判断に使うのが定石
- **外挿の危険**: 学習した時間・空間範囲を超えた予測は保証されません

## 参考文献

- Raissi, Perdikaris, Karniadakis (2019). *"Physics-informed neural networks"*, J. Comput. Phys.
- Wang, Yu, Perdikaris (2022). *"When and why PINNs fail to train"*, JCP.
- Krishnapriyan et al. (2021). *"Characterizing possible failure modes in PINNs"*, NeurIPS.
