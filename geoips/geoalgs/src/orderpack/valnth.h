      Integer(kind=kk), Intent (In) :: NORD
      Integer(kind=kk) :: NDON, JHIG, JLOW, IHIG
      Integer(kind=kk) :: IMIL, IFIN, ICRS, IDCR, ILOW
      Integer(kind=kk) :: JLM2, JLM1, JHM2, JHM1, INTH
!
      NDON = SIZE (XDONT)
      INTH = MAX (MIN (NORD, NDON), 1)
!
!    First loop is used to fill-in XLOWT, XHIGT at the same time
!
      If (NDON < 2) Then
         If (INTH == 1) VALNTH = XDONT (1)
         Return
      End If
!
!  One chooses a pivot, best estimate possible to put fractile near
!  mid-point of the set of low values.
!
      If (XDONT(2) < XDONT(1)) Then
         XLOWT (1) = XDONT(2)
         XHIGT (1) = XDONT(1)
      Else
         XLOWT (1) = XDONT(1)
         XHIGT (1) = XDONT(2)
      End If
!
      If (NDON < 3) Then
         If (INTH == 1) VALNTH = XLOWT (1)
         If (INTH == 2) VALNTH = XHIGT (1)
         Return
      End If
!
      If (XDONT(3) < XHIGT(1)) Then
         XHIGT (2) = XHIGT (1)
         If (XDONT(3) < XLOWT(1)) Then
            XHIGT (1) = XLOWT (1)
            XLOWT (1) = XDONT(3)
         Else
            XHIGT (1) = XDONT(3)
         End If
      Else
         XHIGT (2) = XDONT(3)
      End If
!
      If (NDON < 4) Then
         If (INTH == 1) Then
             VALNTH = XLOWT (1)
         Else
             VALNTH = XHIGT (INTH - 1)
         End If
         Return
      End If
!
      If (XDONT(NDON) < XHIGT(1)) Then
         XHIGT (3) = XHIGT (2)
         XHIGT (2) = XHIGT (1)
         If (XDONT(NDON) < XLOWT(1)) Then
            XHIGT (1) = XLOWT (1)
            XLOWT (1) = XDONT(NDON)
         Else
            XHIGT (1) = XDONT(NDON)
         End If
      Else
         XHIGT (3) = XDONT(NDON)
      End If
!
      If (NDON < 5) Then
         If (INTH == 1) Then
             VALNTH = XLOWT (1)
         Else
             VALNTH = XHIGT (INTH - 1)
         End If
         Return
      End If
!

      JLOW = 1
      JHIG = 3
      XPIV = XLOWT(1) + REAL(2*INTH)/REAL(NDON+INTH) * (XHIGT(3)-XLOWT(1))
      If (XPIV >= XHIGT(1)) Then
         XPIV = XLOWT(1) + REAL(2*INTH)/REAL(NDON+INTH) * &
                           (XHIGT(2)-XLOWT(1))
         If (XPIV >= XHIGT(1)) &
             XPIV = XLOWT(1) + REAL (2*INTH) / REAL (NDON+INTH) * &
                               (XHIGT(1)-XLOWT(1))
      End If
      XPIV0 = XPIV
!
!  One puts values > pivot in the end and those <= pivot
!  at the beginning. This is split in 2 cases, so that
!  we can skip the loop test a number of times.
!  As we are also filling in the work arrays at the same time
!  we stop filling in the XHIGT array as soon as we have more
!  than enough values in XLOWT.
!
!
      If (XDONT(NDON) > XPIV) Then
         ICRS = 3
         Do
            ICRS = ICRS + 1
            If (XDONT(ICRS) > XPIV) Then
               If (ICRS >= NDON) Exit
               JHIG = JHIG + 1
               XHIGT (JHIG) = XDONT(ICRS)
            Else
               JLOW = JLOW + 1
               XLOWT (JLOW) = XDONT(ICRS)
               If (JLOW >= INTH) Exit
            End If
         End Do
!
!  One restricts further processing because it is no use
!  to store more high values
!
         If (ICRS < NDON-1) Then
            Do
               ICRS = ICRS + 1
               If (XDONT(ICRS) <= XPIV) Then
                  JLOW = JLOW + 1
                  XLOWT (JLOW) = XDONT(ICRS)
               Else If (ICRS >= NDON) Then
                  Exit
               End If
            End Do
         End If
!
!
      Else
!
!  Same as above, but this is not as easy to optimize, so the
!  DO-loop is kept
!
         Do ICRS = 4, NDON - 1
            If (XDONT(ICRS) > XPIV) Then
               JHIG = JHIG + 1
               XHIGT (JHIG) = XDONT(ICRS)
            Else
               JLOW = JLOW + 1
               XLOWT (JLOW) = XDONT(ICRS)
               If (JLOW >= INTH) Exit
            End If
         End Do
!
         If (ICRS < NDON-1) Then
            Do
               ICRS = ICRS + 1
               If (XDONT(ICRS) <= XPIV) Then
                  If (ICRS >= NDON) Exit
                  JLOW = JLOW + 1
                  XLOWT (JLOW) = XDONT(ICRS)
               End If
            End Do
         End If
      End If
!
      JLM2 = 0
      JLM1 = 0
      JHM2 = 0
      JHM1 = 0
      Do
         If (JLM2 == JLOW .And. JHM2 == JHIG) Then
!
!   We are oscillating. Perturbate by bringing JLOW closer by one
!   to INTH
!
             If (INTH > JLOW) Then
                XMIN = XHIGT(1)
                IHIG = 1
                Do ICRS = 2, JHIG
                   If (XHIGT(ICRS) < XMIN) Then
                      XMIN = XHIGT(ICRS)
                      IHIG = ICRS
                   End If
                End Do
!
                JLOW = JLOW + 1
                XLOWT (JLOW) = XHIGT (IHIG)
                XHIGT (IHIG) = XHIGT (JHIG)
                JHIG = JHIG - 1
             Else

                XMAX = XLOWT (JLOW)
                JLOW = JLOW - 1
                Do ICRS = 1, JLOW
                   If (XLOWT(ICRS) > XMAX) Then
                      XWRK = XMAX
                      XMAX = XLOWT(ICRS)
                      XLOWT (ICRS) = XWRK
                   End If
                End Do
             End If
         End If
         JLM2 = JLM1
         JLM1 = JLOW
         JHM2 = JHM1
         JHM1 = JHIG
!
!   We try to bring the number of values in the low values set
!   closer to INTH.
!
         Select Case (INTH-JLOW)
         Case (2:)
!
!   Not enough values in low part, at least 2 are missing
!
            INTH = INTH - JLOW
            JLOW = 0
            Select Case (JHIG)
!!!!!           CASE DEFAULT
!!!!!              write (unit=*,fmt=*) "Assertion failed"
!!!!!              STOP
!
!   We make a special case when we have so few values in
!   the high values set that it is bad performance to choose a pivot
!   and apply the general algorithm.
!
            Case (2)
               If (XHIGT(1) <= XHIGT(2)) Then
                  JLOW = JLOW + 1
                  XLOWT (JLOW) = XHIGT (1)
                  JLOW = JLOW + 1
                  XLOWT (JLOW) = XHIGT (2)
               Else
                  JLOW = JLOW + 1
                  XLOWT (JLOW) = XHIGT (2)
                  JLOW = JLOW + 1
                  XLOWT (JLOW) = XHIGT (1)
               End If
               Exit
!
            Case (3)
!
!
               XWRK1 = XHIGT (1)
               XWRK2 = XHIGT (2)
               XWRK3 = XHIGT (3)
               If (XWRK2 < XWRK1) Then
                  XHIGT (1) = XWRK2
                  XHIGT (2) = XWRK1
                  XWRK2 = XWRK1
               End If
               If (XWRK2 > XWRK3) Then
                  XHIGT (3) = XWRK2
                  XHIGT (2) = XWRK3
                  XWRK2 = XWRK3
                  If (XWRK2 < XHIGT(1)) Then
                     XHIGT (2) = XHIGT (1)
                     XHIGT (1) = XWRK2
                  End If
               End If
               JHIG = 0
               Do ICRS = JLOW + 1, INTH
                  JHIG = JHIG + 1
                  XLOWT (ICRS) = XHIGT (JHIG)
               End Do
               JLOW = INTH
               Exit
!
            Case (4:)
!
!
               XPIV0 = XPIV
               IFIN = JHIG
!
!  One chooses a pivot from the 2 first values and the last one.
!  This should ensure sufficient renewal between iterations to
!  avoid worst case behavior effects.
!
               XWRK1 = XHIGT (1)
               XWRK2 = XHIGT (2)
               XWRK3 = XHIGT (IFIN)
               If (XWRK2 < XWRK1) Then
                  XHIGT (1) = XWRK2
                  XHIGT (2) = XWRK1
                  XWRK2 = XWRK1
               End If
               If (XWRK2 > XWRK3) Then
                  XHIGT (IFIN) = XWRK2
                  XHIGT (2) = XWRK3
                  XWRK2 = XWRK3
                  If (XWRK2 < XHIGT(1)) Then
                     XHIGT (2) = XHIGT (1)
                     XHIGT (1) = XWRK2
                  End If
               End If
!
               XWRK1 = XHIGT (1)
               JLOW = JLOW + 1
               XLOWT (JLOW) = XWRK1
               XPIV = XWRK1 + 0.5 * (XHIGT(IFIN)-XWRK1)
!
!  One takes values <= pivot to XLOWT
!  Again, 2 parts, one where we take care of the remaining
!  high values because we might still need them, and the
!  other when we know that we will have more than enough
!  low values in the end.
!
               JHIG = 0
               Do ICRS = 2, IFIN
                  If (XHIGT(ICRS) <= XPIV) Then
                     JLOW = JLOW + 1
                     XLOWT (JLOW) = XHIGT (ICRS)
                     If (JLOW >= INTH) Exit
                  Else
                     JHIG = JHIG + 1
                     XHIGT (JHIG) = XHIGT (ICRS)
                  End If
               End Do
!
               Do ICRS = ICRS + 1, IFIN
                  If (XHIGT(ICRS) <= XPIV) Then
                     JLOW = JLOW + 1
                     XLOWT (JLOW) = XHIGT (ICRS)
                  End If
               End Do
            End Select
!
!
         Case (1)
!
!  Only 1 value is missing in low part
!
            XMIN = XHIGT(1)
            IHIG = 1
            Do ICRS = 2, JHIG
               If (XHIGT(ICRS) < XMIN) Then
                  XMIN = XHIGT(ICRS)
                  IHIG = ICRS
               End If
            End Do
!
            VALNTH = XHIGT (IHIG)
            Return
!
!
         Case (0)
!
!  Low part is exactly what we want
!
            Exit
!
!
         Case (-5:-1)
!
!  Only few values too many in low part
!
            XHIGT (1) = XLOWT (1)
            ILOW = 1 + INTH - JLOW
            Do ICRS = 2, INTH
               XWRK = XLOWT (ICRS)
               Do IDCR = ICRS - 1, MAX (1, ILOW), - 1
                  If (XWRK < XHIGT(IDCR)) Then
                     XHIGT (IDCR+1) = XHIGT (IDCR)
                  Else
                     Exit
                  End If
               End Do
               XHIGT (IDCR+1) = XWRK
               ILOW = ILOW + 1
            End Do
!
            XWRK1 = XHIGT(INTH)
            ILOW = 2*INTH - JLOW
            Do ICRS = INTH + 1, JLOW
               If (XLOWT (ICRS) < XWRK1) Then
                  XWRK = XLOWT (ICRS)
                  Do IDCR = INTH - 1, MAX (1, ILOW), - 1
                     If (XWRK >= XHIGT(IDCR)) Exit
                     XHIGT (IDCR+1) = XHIGT (IDCR)
                  End Do
                  XHIGT (IDCR+1) = XLOWT (ICRS)
                  XWRK1 = XHIGT(INTH)
               End If
               ILOW = ILOW + 1
            End Do
!
            VALNTH = XHIGT(INTH)
            Return
!
!
         Case (:-6)
!
! last case: too many values in low part
!

            IMIL = (JLOW+1) / 2
            IFIN = JLOW
!
!  One chooses a pivot from 1st, last, and middle values
!
            If (XLOWT(IMIL) < XLOWT(1)) Then
               XWRK = XLOWT (1)
               XLOWT (1) = XLOWT (IMIL)
               XLOWT (IMIL) = XWRK
            End If
            If (XLOWT(IMIL) > XLOWT(IFIN)) Then
               XWRK = XLOWT (IFIN)
               XLOWT (IFIN) = XLOWT (IMIL)
               XLOWT (IMIL) = XWRK
               If (XLOWT(IMIL) < XLOWT(1)) Then
                  XWRK = XLOWT (1)
                  XLOWT (1) = XLOWT (IMIL)
                  XLOWT (IMIL) = XWRK
               End If
            End If
            If (IFIN <= 3) Exit
!
            XPIV = XLOWT(1) + REAL(INTH)/REAL(JLOW+INTH) * &
                              (XLOWT(IFIN)-XLOWT(1))

!
!  One takes values > XPIV to XHIGT
!
            JHIG = 0
            JLOW = 0
!
            If (XLOWT(IFIN) > XPIV) Then
               ICRS = 0
               Do
                  ICRS = ICRS + 1
                  If (XLOWT(ICRS) > XPIV) Then
                     JHIG = JHIG + 1
                     XHIGT (JHIG) = XLOWT (ICRS)
                     If (ICRS >= IFIN) Exit
                  Else
                     JLOW = JLOW + 1
                     XLOWT (JLOW) = XLOWT (ICRS)
                     If (JLOW >= INTH) Exit
                  End If
               End Do
!
               If (ICRS < IFIN) Then
                  Do
                     ICRS = ICRS + 1
                     If (XLOWT(ICRS) <= XPIV) Then
                        JLOW = JLOW + 1
                        XLOWT (JLOW) = XLOWT (ICRS)
                     Else
                        If (ICRS >= IFIN) Exit
                     End If
                  End Do
               End If
            Else
               Do ICRS = 1, IFIN
                  If (XLOWT(ICRS) > XPIV) Then
                     JHIG = JHIG + 1
                     XHIGT (JHIG) = XLOWT (ICRS)
                  Else
                     JLOW = JLOW + 1
                     XLOWT (JLOW) = XLOWT (ICRS)
                     If (JLOW >= INTH) Exit
                  End If
               End Do
!
               Do ICRS = ICRS + 1, IFIN
                  If (XLOWT(ICRS) <= XPIV) Then
                     JLOW = JLOW + 1
                     XLOWT (JLOW) = XLOWT (ICRS)
                  End If
               End Do
            End If
!
         End Select
!
      End Do
!
!  Now, we only need to find maximum of the 1:INTH set
!
      VALNTH = MAXVAL (XLOWT (1:INTH))
      Return
