select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select fk_facility
from "healthdata_dw"."dw_gold"."fact_hospital_production"
where fk_facility is null



      
    ) dbt_internal_test