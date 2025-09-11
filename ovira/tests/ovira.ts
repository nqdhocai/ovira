import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import { Ovira } from "../target/types/ovira";
import { PublicKey } from "@solana/web3.js";
import * as dotenv from "dotenv";
import { bs58 } from "@coral-xyz/anchor/dist/cjs/utils/bytes";
import { Account, getAssociatedTokenAddressSync, getOrCreateAssociatedTokenAccount } from "@solana/spl-token";

dotenv.config();

describe("ovira", () => {
  // Configure the client to use the local cluster.
  const provider = new anchor.AnchorProvider(
    new anchor.web3.Connection(process.env.RPC_URL!, "confirmed"),
    new anchor.Wallet(anchor.web3.Keypair.fromSecretKey(bs58.decode(process.env.PAYER_SECRET_KEY!))),
    { commitment: "confirmed" }
  );

  anchor.setProvider(provider);
  const program = anchor.workspace.Ovira as Program<Ovira>;
  const payer = provider.wallet as anchor.Wallet;

  const token_mint = new PublicKey(process.env.USDC_TOKEN_MINT);
  let vaultPda: PublicKey;
  let vaultConfigPda: PublicKey;
  let userPosition: PublicKey;
  let vaultTokenAccount: PublicKey;

  before(async () => {
    vaultConfigPda = PublicKey.findProgramAddressSync(
      [Buffer.from("vault_config"), token_mint.toBuffer()],
      program.programId
    )[0];

    vaultPda = PublicKey.findProgramAddressSync(
      [Buffer.from("vault"), token_mint.toBuffer()],
      program.programId,
    )[0];

    userPosition = PublicKey.findProgramAddressSync(
      [Buffer.from("user_position"), token_mint.toBuffer(), payer.publicKey.toBuffer()],
      program.programId
    )[0];

    await getOrCreateAssociatedTokenAccount (provider.connection, payer.payer, token_mint, vaultConfigPda, true);
    vaultTokenAccount = getAssociatedTokenAddressSync(token_mint, vaultConfigPda, true);
  })

  // it("Initilize ", async () => {
  //   const performanceFee = 1000;
  //   const managementFee = 500;
  //   const pools = ["a", "b", "c", "d", "e"];
    
  //   const tx = await program.methods
  //     .initialize(performanceFee, managementFee, pools)
  //     .accountsPartial({
  //       admin: payer.publicKey,
  //       vaultConfig: vaultConfigPda,
  //       vault: vaultPda,
  //       vaultTokenAccount: vaultTokenAccount,
  //       tokenMint: token_mint,
  //       associatedTokenProgram: anchor.utils.token.ASSOCIATED_PROGRAM_ID,
  //       tokenProgram: anchor.utils.token.TOKEN_PROGRAM_ID,
  //       systemProgram: anchor.web3.SystemProgram.programId,
  //       rent: anchor.web3.SYSVAR_RENT_PUBKEY,
  //     })
  //     .rpc();

  //   console.log("Initilize transaction successful: ", tx);

  //   const vaultConfig = await program.account.vaultConfig.fetch(vaultConfigPda);
  //   const vault = await program.account.vault.fetch(vaultPda);

  //   console.log(vault, vaultConfig);
    
  // })

  // it("Deposit", async () => {
  //   const userTokenAccount = (await getOrCreateAssociatedTokenAccount(
  //     provider.connection,
  //     payer.payer,
  //     token_mint,
  //     payer.publicKey,
  //     true
  //   )).address;

  //   const tx = await program.methods.deposit(
  //     new anchor.BN(10)
  //   )
  //   .accountsPartial({
  //       signer: payer.publicKey,
  //       userPosition: userPosition,
  //       vaultConfig: vaultConfigPda,
  //       vault: vaultPda,
  //       vaultTokenAccount: vaultTokenAccount,
  //       userTokenAccount: userTokenAccount,
  //       tokenMint: token_mint,
  //       associatedTokenProgram: anchor.utils.token.ASSOCIATED_PROGRAM_ID,
  //       tokenProgram: anchor.utils.token.TOKEN_PROGRAM_ID,
  //       systemProgram: anchor.web3.SystemProgram.programId,      
  //   })
  //   .rpc();

  //   console.log("Successfully deposit to vault", tx);
  // })

  it("Withdraw", async () => {
    const userTokenAccount = getAssociatedTokenAddressSync(
      token_mint,
      payer.publicKey,
      true
    );

    const tx = await program.methods.withdraw(
      new anchor.BN(10)
    )
    .accountsPartial({
        signer: payer.publicKey,
        userPosition: userPosition,
        vaultConfig: vaultConfigPda,
        vault: vaultPda,
        vaultTokenAccount: vaultTokenAccount,
        userTokenAccount: userTokenAccount,
        tokenMint: token_mint,
        associatedTokenProgram: anchor.utils.token.ASSOCIATED_PROGRAM_ID,
        tokenProgram: anchor.utils.token.TOKEN_PROGRAM_ID,
        systemProgram: anchor.web3.SystemProgram.programId,      
    })
    .rpc();

    console.log("Successfully withdraw from vault", tx);
  })

});
