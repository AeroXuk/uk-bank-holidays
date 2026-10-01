-- UK bank holidays: Easter Sunday helper (mssql)
-- Safe to re-run: CREATE OR ALTER replaces the function.
-- A modified version of the MS-SQL algorithm posted on https://en.wikipedia.org/wiki/Computus#Software,
-- which is based on the Anonymous Gregorian Algorithm (Meeus/Jones/Butcher). Valid for 1583 onwards.
CREATE OR ALTER FUNCTION [dbo].[CalculateEasterDay] ( @Year int )
RETURNS date AS
BEGIN
    DECLARE @a int, @b int, @d int
        ,@MC int = @Year %  19 -- 19 Year Metonic Cycle
        ,@SR int = @Year % 100 -- Secular Remainder
        ,@SN int = @Year / 100 -- Secular Number
    ;
    SELECT
        @a = ((19 * @MC + @SN - (@SN / 4) - ((@SN - ((@SN + 8) / 25) + 1) / 3) + 15) % 30),
        @b = ((32 + 2 * (@SN % 4) + 2 * (@SR / 4) - @a - (@SR % 4)) % 7),
        @d = @a + @b - 7 * ((@MC + 11 * @a + 22 * @b) / 451) + 114
    ;
    RETURN DATEFROMPARTS(@Year, @d / 31, (@d % 31) + 1);
END;
GO
