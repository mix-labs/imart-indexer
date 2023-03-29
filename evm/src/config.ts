import * as env from "dotenv";
env.config();

export const {
  ALCHEMY_API,
  INFURA_API,
  CONTRACT_CURATION,
  CONTRACT_SINGLE_COLLECTIVE,
  CONTRACT_MULTIPLE_COLLECTIVE,
  DURATION_MILLIS,
  PRIVATE_KEY_ALICE,
  PRIVATE_KEY_BOB,
  PRIVATE_KEY_CICI,
  PRIVATE_KEY_TEST_ONLY,
  MNEMONIC,
  PROVIDER_ENDPOINT_1,
  PROVIDER_ENDPOINT_2,
  PROVIDER_ENDPOINT_3,
  PROVIDERS,
  EVENTOFFSET_ID
} = process.env;
