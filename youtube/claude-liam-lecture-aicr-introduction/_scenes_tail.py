

# attach the midpoint guard (see ST); the classes stay literal `(Scene)` for run.sh scene discovery
for _cls in (B10_SixIntoOne, B11_GpuCount, B12_Around, B13_ExplorerToAicr, B20_Proposal, B22_Username, B30_ThreePlaces, B31_SevenDays, B32_ScratchPurge, B40_PartitionTable, B41_BatchVsDevel, B42_IdleCards, B43_IdleCancel, B55_OodToSlurm, B61_YearlyReview, B62_DataGoesHome):
    _cls.play = ST.play
