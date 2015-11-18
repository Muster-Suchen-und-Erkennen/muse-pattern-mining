DELETE FROM basiselementdesign WHERE Designname =''
Go
DELETE FROM basiselementfunktion WHERE Funktionsname = ''
Go
DELETE FROM basiselementzustand WHERE Zustandsname = ''
Go
DELETE FROM teilelementform WHERE Formname =''
Go
DELETE FROM teilelementzustand WHERE Zustandsname = ''
Go
DELETE FROM kostuemspielzeit WHERE Spielzeit= ''
Go
DELETE FROM filmgenre WHERE Genre = ''
Go
DELETE FROM kostuemalterseindruck WHERE Alterseindruck = ''
Go
UPDATE rolle SET Rollenvorname = NULL WHERE Rollenvorname = ''
UPDATE rolle SET Rollennachname = NULL WHERE Rollennachname = ''
UPDATE rolle SET Geschlecht = NULL WHERE Geschlecht = ''
UPDATE rolle SET DominanterAlterseindruck = NULL WHERE DominanterAlterseindruck = ''
UPDATE rolle SET DominantesAlter = NULL WHERE DominantesAlter = ''
UPDATE rolle SET Schauspielervorname = NULL WHERE Schauspielervorname = ''
UPDATE rolle SET Schauspielernachname = NULL WHERE Schauspielernachname = ''
UPDATE rolle SET Rollenrelevanz = NULL WHERE Rollenrelevanz = ''
Go
UPDATE kostuem SET Ortsbegebenheit = NULL WHERE Ortsbegebenheit = ''
UPDATE kostuem SET DominanteFarbe = NULL WHERE DominanteFarbe = ''
UPDATE kostuem SET DominanteFunktion = NULL WHERE DominanteFunktion = ''
UPDATE kostuem SET DominanterZustand = NULL WHERE DominanterZustand = ''
Go
