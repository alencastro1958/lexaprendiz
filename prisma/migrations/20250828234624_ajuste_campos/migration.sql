/*
  Warnings:

  - You are about to drop the column `criadoEm` on the `Consulta` table. All the data in the column will be lost.
  - You are about to drop the column `pergunta` on the `Consulta` table. All the data in the column will be lost.
  - You are about to drop the column `resposta` on the `Consulta` table. All the data in the column will be lost.
  - Added the required column `perguntaA` to the `Consulta` table without a default value. This is not possible if the table is not empty.
  - Added the required column `respostaA` to the `Consulta` table without a default value. This is not possible if the table is not empty.

*/
-- RedefineTables
PRAGMA defer_foreign_keys=ON;
PRAGMA foreign_keys=OFF;
CREATE TABLE "new_Consulta" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "perguntaA" TEXT NOT NULL,
    "respostaA" TEXT NOT NULL,
    "criaçãoEm" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO "new_Consulta" ("id") SELECT "id" FROM "Consulta";
DROP TABLE "Consulta";
ALTER TABLE "new_Consulta" RENAME TO "Consulta";
PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;
