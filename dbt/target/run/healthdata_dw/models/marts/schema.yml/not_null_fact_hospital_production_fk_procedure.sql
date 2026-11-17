select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select fk_procedure
from "healthdata_dw"."dw_gold"."fact_hospital_production"
where fk_procedure is null



      
    ) dbt_internal_test